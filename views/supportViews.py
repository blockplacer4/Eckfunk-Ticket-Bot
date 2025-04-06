# supportViews.py (Beispiel - Anwenden auf alle Modal-Dateien!)
"""
Discord Ticket Bot - Support Views Modul
"""

import asyncio
import datetime
import discord
import mongodb
from cogs import tickets # Import tickets cog for the view

class Modal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add items as before...
        self.add_item(
            discord.ui.InputText(label="Kategorisiere dein Anliegen...")
        )
        self.add_item(
            discord.ui.InputText(
                label="Erkläre uns dein Anliegen...",
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Wir bestrafen troll Tickets, verstanden?",
                placeholder="Ja!"
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Entscheidungen werden akzeptiert, verstanden?",
                placeholder="Ja!"
            )
        )

    async def callback(self, interaction: discord.Interaction):
        # --- Sammle Öffnungskontext ---
        opening_context = {}
        for child in self.children:
            if isinstance(child, discord.ui.InputText): # Sicherstellen, dass es InputText ist
                opening_context[child.label] = child.value
        # --- Ende Sammeln ---

        # Embeds für den Öffnungsprozess (können auch create_embed nutzen)
        embed = discord.Embed(title="⏳ Dein Ticket wird geöffnet...", description="Bitte habe einen kurzen Moment Geduld...", color=0xff5252)
        await interaction.response.send_message(embed=embed, ephemeral=True) # Use send_message for initial modal response

        # ... (restliche Logik zum Kanal erstellen, Permissions setzen etc.) ...
        # Hole Konfigurationsdaten
        config_id = 2104
        config_data = await mongodb.db["config"].find_one({"_id": config_id})
        if not config_data:
            await interaction.followup.send("Fehler: Bot-Konfiguration nicht gefunden.", ephemeral=True)
            return

        category_id = config_data.get("category")
        ping_role_id = config_data.get("ping_role")
        member_role_id = config_data.get("member_role")
        ticket_channel_id = config_data.get("channel") # Panel channel ID for position reference

        if not all([category_id, ping_role_id, member_role_id, ticket_channel_id]):
             await interaction.followup.send("Fehler: Unvollständige Bot-Konfiguration (Kategorie, Rollen oder Kanal fehlt).", ephemeral=True)
             return

        category = discord.utils.get(interaction.guild.categories, id=category_id)
        ping_role = interaction.guild.get_role(ping_role_id)
        member_role = interaction.guild.get_role(member_role_id)
        reference_channel = interaction.guild.get_channel(ticket_channel_id)

        if not category or not ping_role or not member_role or not reference_channel:
             await interaction.followup.send("Fehler: Konfigurierte Kategorie, Rollen oder Referenzkanal nicht gefunden.", ephemeral=True)
             return

        ticket_id = await mongodb.get_new_ticket_id()
        user = interaction.user

        # Update status embed
        embed.description = "🔍 Die richtige Kategorie wird gesucht..."
        await interaction.edit_original_response(embed=embed)
        await asyncio.sleep(0.5)

        embed.description = "➕ Der Channel wird erstellt..."
        await interaction.edit_original_response(embed=embed)
        try:
            created_channel = await interaction.guild.create_text_channel(
                name=f"support-{user.name}-{ticket_id:04d}",
                category=category,
                position=reference_channel.position, # Position relative to panel channel
                reason=f"Support Ticket #{ticket_id} für {user}"
            )
        except Exception as e:
            embed.title = "❌ Fehler"
            embed.description = f"Kanal konnte nicht erstellt werden: {e}"
            embed.color = discord.Color.red()
            await interaction.edit_original_response(embed=embed)
            return
        await asyncio.sleep(0.5)


        embed.description = "🔒 Die Permissions werden gesetzt..."
        await interaction.edit_original_response(embed=embed)
        try:
            # Set permissions (using overwrites for clarity)
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
                user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
                ping_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
                member_role: discord.PermissionOverwrite(view_channel=False) # Deny view for member role explicitly
            }
            await created_channel.edit(overwrites=overwrites, reason="Ticket Permissions setzen")
        except Exception as e:
            embed.title = "❌ Fehler"
            embed.description = f"Permissions konnten nicht gesetzt werden: {e}"
            embed.color = discord.Color.red()
            await interaction.edit_original_response(embed=embed)
            # Consider deleting the channel if permissions fail critically
            # await created_channel.delete(reason="Permission setup failed")
            return
        await asyncio.sleep(0.5)

        embed.description = "✉️ Die Startnachricht wird gesendet..."
        await interaction.edit_original_response(embed=embed)

        # Erstelle das Embed für den Ticket-Kanal
        ticket_embed = discord.Embed(
            title="Support Ticket",
            color=discord.Color(config_data.get("color", 0xff5252)),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
            description="Wir bitten um dein Verständnis, wenn unsere Teammitglieder manchmal etwas länger für eine Antwort brauchen."
        )
        ticket_embed.set_author(name=user.name, icon_url=user.display_avatar.url)
        ticket_embed.add_field(name="Status", value="🟢 Offen", inline=True)
        ticket_embed.add_field(name="Ticket ID", value=f"`#{ticket_id:04d}`", inline=True)
        ticket_embed.add_field(name="Erstellt von", value=user.mention, inline=False)

        # Füge Öffnungskontext zum Ticket-Embed hinzu
        context_str = "\n".join([f"**{label}:** {value}" for label, value in opening_context.items()])
        if context_str:
            ticket_embed.add_field(name="Deine Angaben", value=context_str, inline=False)

        try:
            # Sende Nachricht in den NEUEN Kanal
            message_obj = await created_channel.send(
                content=f"{ping_role.mention} {user.mention}",
                embed=ticket_embed,
                view=tickets.TicketEmbedButtons() # Use the view from tickets cog
            )
        except Exception as e:
            embed.title = "❌ Fehler"
            embed.description = f"Startnachricht konnte nicht gesendet werden: {e}"
            embed.color = discord.Color.red()
            await interaction.edit_original_response(embed=embed)
            # Consider deleting the channel
            # await created_channel.delete(reason="Failed to send initial message")
            return

        # Speichere Ticket in DB *mit* Öffnungskontext
        await mongodb.insert_new_ticket(
            ticket_id=ticket_id,
            user_id=user.id,
            ticket_type="support", # Oder basierend auf Modal
            last_message=datetime.datetime.now(datetime.timezone.utc),
            channel_id=created_channel.id,
            status="open",
            embed_message=message_obj.id,
            opening_context=opening_context # Pass context here
        )

        # Bestätigung für den User (ephemeral)
        confirm_embed = discord.Embed(
            title="✅ Ticket erstellt",
            description=f"Dein Ticket wurde erfolgreich erstellt!\n\n➡️ {message_obj.jump_url}",
            colour=discord.Color.green(),
            timestamp=datetime.datetime.now(datetime.timezone.utc),
        )
        await interaction.edit_original_response(embed=confirm_embed, view=None) # Remove initial "loading" embed

