import datetime
import discord
from discord.ext import commands
import io
import pytz
import mongodb
import asyncio # <--- Hinzugefügt
from views import (
    supportViews,
    fastreportViews,
    partyBewerbungViews,
    addUserViews,
)

berlin_tz = pytz.timezone('Europe/Berlin')

def create_embed(title, description, color, ctx_or_interaction=None):
    embed = discord.Embed(title=title, description=description, color=color)
    if ctx_or_interaction:
        user = getattr(ctx_or_interaction, 'user', getattr(ctx_or_interaction, 'author', None))
        if user:
            embed.set_author(name=user.name, icon_url=user.display_avatar.url)
    embed.timestamp = datetime.datetime.now(pytz.utc)
    return embed


class PanelButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(style=discord.ButtonStyle.success, label="Support", emoji="🎫", custom_id="support-button")
    async def support_callback(self, button, interaction):
        await interaction.response.send_modal(supportViews.Modal(title="✨ Support Ticket"))

    @discord.ui.button(style=discord.ButtonStyle.primary, label="Fast Report", emoji="⚡", custom_id="fastreport-button")
    async def fastreport_callback(self, button, interaction):
        await interaction.response.send_modal(fastreportViews.Modal(title="⚡ Fast Report"))

    @discord.ui.button(style=discord.ButtonStyle.secondary, label="Partei Bewerbung", emoji="📝", custom_id="partei-bewerbung-button")
    async def partei_bewerbung_callback(self, button, interaction):
        await interaction.response.send_modal(partyBewerbungViews.Modal(title="📝 Partei Bewerbungs Ticket"))


class TicketEmbedButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(style=discord.ButtonStyle.red, label="Schließen", emoji="🔒", custom_id="closing-button")
    async def close_callback(self, button, interaction):
        embed = create_embed("⚠️ Ticket schließen", "Möchtest du dieses Ticket wirklich schließen und archivieren? Diese Aktion kann nicht rückgängig gemacht werden.", discord.Color.orange(), interaction)
        embed.set_footer(text="Alle Nachrichten werden in einem Transkript gespeichert.")
        # Nachricht öffentlich senden (nicht ephemeral)
        await interaction.response.send_message(embed=embed, view=ConfirmClosingButton(), ephemeral=False) 

    @discord.ui.button(style=discord.ButtonStyle.primary, label="User hinzufügen", emoji="👥", custom_id="add-user-button")
    async def add_button(self, button, interaction):
        await interaction.response.send_modal(addUserViews.Modal(title="👥 User zum Ticket hinzufügen"))


class ConfirmClosingButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        label="Bestätigen",
        emoji="✅",
        custom_id="confirm-closing-button",
    )
    async def close_button_callback(self, button: discord.ui.Button, interaction: discord.Interaction):
        # Sofort die (jetzt öffentliche) Bestätigungsnachricht löschen
        try:
            await interaction.message.delete()
        except (discord.NotFound, discord.HTTPException) as e:
            # Logge den Fehler, falls er weiterhin auftritt, aber fahre fort
            print(f"Warning: Could not delete confirmation message: {e}") 
        
        # Zeige Ladeanimation (ephemeral für den Klicker)
        await interaction.response.defer(ephemeral=True)
        
        # Hole wichtige Informationen
        channel = interaction.channel
        guild = interaction.guild
        bot = interaction.client
        config_id = 2104

        # Lade Konfigurationsdaten
        config_data = await mongodb.db["config"].find_one({"_id": config_id})
        if not config_data:
             embed = create_embed("❌ Fehler beim Schließen", "Bot-Konfiguration nicht gefunden. Bitte kontaktiere einen Administrator.", discord.Color.red(), interaction)
             await interaction.followup.send(embed=embed, ephemeral=True)
             return

        # Farben definieren
        default_color = discord.Color(config_data.get("color", 0xff5252))
        error_color = discord.Color.red()
        warning_color = discord.Color.orange()
        success_color = discord.Color.green()
        info_color = discord.Color.blue()

        # Lade Ticket-Daten
        ticket_doc = await mongodb.find_ticket_by_channel_id(channel.id)
        if not ticket_doc:
            embed = create_embed("❌ Fehler beim Schließen", "Ticket-Daten nicht in der Datenbank gefunden. Bitte kontaktiere einen Administrator.", error_color, interaction)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        ticket_id = ticket_doc["_id"]
        ticket_opener_id = ticket_doc.get("user_id")
        opening_context = ticket_doc.get("opening_context")

        # Lade Transkript-Kanal
        transcript_channel_id = config_data.get("transcript_channel")
        if not transcript_channel_id:
            embed = create_embed("❌ Fehler beim Schließen", "Transkript-Kanal nicht konfiguriert. Bitte kontaktiere einen Administrator.", error_color, interaction)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        transcript_forum = guild.get_channel(transcript_channel_id)
        if not transcript_forum or not isinstance(transcript_forum, discord.ForumChannel):
            embed = create_embed("❌ Fehler beim Schließen", "Konfigurierter Transkript-Kanal ist kein Forum-Kanal. Bitte kontaktiere einen Administrator.", error_color, interaction)
            await interaction.followup.send(embed=embed, ephemeral=True)
            return

        # Erstelle Transkript
        transcript_content = []
        # Header mit Styling
        transcript_content.append("=" * 50)
        transcript_content.append(f"📜 TICKET TRANSKRIPT #{ticket_id:04d} 📜")
        transcript_content.append("=" * 50)
        transcript_content.append(f"📋 Kanal: {channel.name} (ID: {channel.id})")
        transcript_content.append(f"👤 Erstellt von: User ID {ticket_opener_id or 'Unbekannt'}")
        transcript_content.append(f"🔒 Geschlossen von: {interaction.user} (ID: {interaction.user.id})")
        transcript_content.append(f"⏰ Geschlossen am: {datetime.datetime.now(berlin_tz).strftime('%d.%m.%Y um %H:%M:%S')} (Europe/Berlin)")
        transcript_content.append("=" * 50)

        # Füge Öffnungskontext hinzu
        if opening_context and isinstance(opening_context, dict):
            transcript_content.append("📝 TICKET INFORMATIONEN 📝")
            transcript_content.append("-" * 50)
            for label, value in opening_context.items():
                formatted_value = "\n".join([f"  {line}" for line in str(value).splitlines()]) if "\n" in str(value) else value
                transcript_content.append(f"• {label}: {formatted_value}")
            transcript_content.append("=" * 50)

        # Nachrichten
        transcript_content.append("💬 NACHRICHTENVERLAUF 💬")
        transcript_content.append("-" * 50)
        message_count = 0
        try:
            async for msg in channel.history(limit=None, oldest_first=True):
                message_count += 1
                local_time = msg.created_at.astimezone(berlin_tz)
                timestamp = local_time.strftime("%d.%m.%Y %H:%M:%S")
                content = msg.clean_content
                attachments = " ".join([f"[Anhang: {att.filename}]({att.url})" for att in msg.attachments])
                
                # Formatiere die Nachricht
                author_line = f"👤 {msg.author} ({msg.author.id})"
                time_line = f"⏰ {timestamp}"
                transcript_content.append(f"{author_line} | {time_line}")
                transcript_content.append(f"➡️ {content}")
                if attachments:
                    transcript_content.append(f"📎 {attachments}")
                transcript_content.append("-" * 50)
            
            transcript_content.append("=" * 50)
            transcript_content.append(f"🏁 ENDE DES TRANSKRIPTS | {message_count} Nachrichten insgesamt")
            transcript_content.append("=" * 50)
        except discord.Forbidden:
             embed = create_embed("❌ Fehler beim Schließen", "Keine Berechtigung, den Nachrichtenverlauf zu lesen. Bitte kontaktiere einen Administrator.", error_color, interaction)
             await interaction.followup.send(embed=embed, ephemeral=True)
             return
        except Exception as e:
             embed = create_embed("❌ Fehler beim Schließen", f"Fehler beim Erstellen des Transkripts: {e}", error_color, interaction)
             await interaction.followup.send(embed=embed, ephemeral=True)
             return

        # Erstelle Transkript-Datei
        transcript_text = "\n".join(transcript_content)
        transcript_file = discord.File(
            io.BytesIO(transcript_text.encode("utf-8")),
            filename=f"transcript-{ticket_id:04d}.txt",
        )
        
        # Erstelle eine Kopie des Transkript-Files für den User
        user_transcript_file = discord.File(
            io.BytesIO(transcript_text.encode("utf-8")),
            filename=f"transcript-{ticket_id:04d}.txt",
        )

        # Erstelle Thread im Forum
        try:
            thread_content = (f"📜 Transkript für Ticket `#{ticket_id:04d}` "
                              f"(Erstellt von User ID: `{ticket_opener_id or 'Unbekannt'}`) - "
                              f"Geschlossen von {interaction.user.mention} am {datetime.datetime.now(berlin_tz).strftime('%d.%m.%Y um %H:%M:%S')}.")
            if len(thread_content) > 2000:
                thread_content = thread_content[:1997] + "..."

            thread = await transcript_forum.create_thread(
                name=f"📜 Ticket #{ticket_id:04d} | {channel.name}",
                content=thread_content,
                file=transcript_file,
                reason=f"Archivierung von Ticket #{ticket_id:04d}",
            )
        except discord.Forbidden:
             embed = create_embed("❌ Fehler beim Schließen", "Keine Berechtigung, Threads im Transkript-Kanal zu erstellen. Bitte kontaktiere einen Administrator.", error_color, interaction)
             await interaction.followup.send(embed=embed, ephemeral=True)
             return
        except Exception as e:
             embed = create_embed("❌ Fehler beim Schließen", f"Fehler beim Erstellen des Threads: {e}", error_color, interaction)
             await interaction.followup.send(embed=embed, ephemeral=True)
             return

        # Aktualisiere Datenbank
        await mongodb.update_ticket_data(
            "tickets",
            ticket_id,
            {"status": "closed", "transcript_thread_id": thread.id},
        )

        # Sende DM an Ticket-Ersteller
        dm_sent = False
        if ticket_opener_id:
            try:
                opener_user = await bot.fetch_user(ticket_opener_id)
                if opener_user:
                    dm_embed = discord.Embed(
                        title=f"🎫 Dein Ticket #{ticket_id:04d} wurde geschlossen",
                        description=(
                            f"### ✅ Ticket erfolgreich geschlossen\n\n"
                            f"Dein Ticket auf dem Server **{guild.name}** wurde von {interaction.user.mention} geschlossen.\n\n"
                            f"📝 **Ticket-Details:**\n"
                            f"• **Ticket-ID:** `#{ticket_id:04d}`\n"
                            f"• **Kanal:** `{channel.name}`\n"
                            f"• **Geschlossen am:** {datetime.datetime.now(berlin_tz).strftime('%d.%m.%Y um %H:%M:%S')}\n\n"
                            f"📎 **Das vollständige Transkript** ist an diese Nachricht angehängt.\n"
                            f"📚 Bitte bewahre es für deine Unterlagen auf."
                        ),
                        color=success_color,
                        timestamp=datetime.datetime.now()
                    )
                    dm_embed.set_thumbnail(url=guild.icon.url if guild.icon else None)
                    dm_embed.set_footer(text=f"{guild.name} • Ticket-System", icon_url=guild.icon.url if guild.icon else None)
                    await opener_user.send(embed=dm_embed, file=user_transcript_file)
                    dm_sent = True
            except Exception as e:
                print(f"Could not DM user {ticket_opener_id}: {e}")

        # Sende Bestätigung an den Moderator (ephemeral)
        confirmation_embed = discord.Embed(
            title="✅ Ticket erfolgreich geschlossen",
            description=(
                f"### 🎫 Ticket `#{ticket_id:04d}` wurde geschlossen\n\n"
                f"📋 **Details:**\n"
                f"• **Ticket-ID:** `#{ticket_id:04d}`\n"
                f"• **Kanal:** `{channel.name}`\n"
                f"• **Geschlossen von:** {interaction.user.mention}\n"
                f"• **Geschlossen am:** {datetime.datetime.now(berlin_tz).strftime('%d.%m.%Y um %H:%M:%S')}\n\n"
                f"📜 **Transkript:** {thread.mention}\n"
            ),
            color=success_color,
            timestamp=datetime.datetime.now()
        )
        
        # Füge DM-Status hinzu
        if dm_sent:
            confirmation_embed.add_field(
                name="📨 Benachrichtigung",
                value="✅ Der Ticketersteller wurde per DM benachrichtigt und hat das Transkript erhalten.",
                inline=False
            )
        elif ticket_opener_id:
            confirmation_embed.add_field(
                name="📨 Benachrichtigung",
                value="⚠️ Der Ticketersteller konnte nicht per DM benachrichtigt werden.",
                inline=False
            )
        
        confirmation_embed.set_footer(text=f"{guild.name} • Ticket-System", icon_url=guild.icon.url if guild.icon else None)
        await interaction.followup.send(embed=confirmation_embed, ephemeral=True)

        # Lösche den Kanal mit Verzögerung
        try:
            # Sende öffentliche Nachricht im Kanal vor dem Löschen
            await channel.send(
                embed=discord.Embed(
                    title="🔒 Ticket wird geschlossen...",
                    description=(
                        f"### ⏳ Dieses Ticket wird in 5 Sekunden geschlossen\n\n"
                        f"📜 Ein Transkript wurde erstellt und archiviert.\n"
                        f"👤 Der Ticketersteller erhält eine Kopie per DM (falls möglich)."
                    ),
                    color=info_color
                ).set_footer(text="Auf Wiedersehen!")
            )
            await asyncio.sleep(5) # Warte 5 Sekunden
            await channel.delete(reason=f"Ticket #{ticket_id:04d} geschlossen und archiviert.")
        except Exception as e:
             # Logge den Fehler, aber der Prozess ist größtenteils abgeschlossen
             print(f"WARN/ERROR: Failed to delete channel {channel.id} for ticket {ticket_id}: {e}") 


class Tickets(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    tickets_group = discord.SlashCommandGroup(
        "tickets",
        "Befehle zur Verwaltung von Tickets und Transkripten",
    )

    @tickets_group.command(
        name="setup",
        description="Richtet das Ticket-System und den Transkript-Kanal ein."
    )
    @commands.has_permissions(administrator=True)
    async def setup(
        self,
        ctx: discord.ApplicationContext,
        channel: discord.TextChannel,
        transcript_channel: discord.abc.GuildChannel,
        member_role: discord.Role,
        ping_role: discord.Role,
        color: str,
    ):
        error_color = discord.Color.red()
        success_color = discord.Color.green()

        if not isinstance(transcript_channel, discord.ForumChannel):
            embed = create_embed("❌ Setup Fehler", "Der angegebene Transkript-Kanal muss ein **Forum-Kanal** sein.", error_color, ctx)
            await ctx.respond(embed=embed, ephemeral=True)
            return

        try:
            color_int = int(color.lstrip('#'), 16)
        except ValueError:
            embed = create_embed("❌ Setup Fehler", "Ungültiges Farbformat. Bitte Hex-Code verwenden (z.B. `ff5252` oder `#ff5252`).", error_color, ctx)
            await ctx.respond(embed=embed, ephemeral=True)
            return

        panel_embed = discord.Embed(
            title="🎫 Ticket Support System",
            description=(
                "### 👋 Willkommen beim Ticket Support!\n\n"
                "Unser System ermöglicht dir eine schnelle und einfache Möglichkeit, "
                "Unterstützung für deine Anliegen zu erhalten.\n\n"
                "**So funktioniert es:**\n"
                "1️⃣ Wähle eine der Optionen unten\n"
                "2️⃣ Fülle das Formular aus\n"
                "3️⃣ Warte auf Antwort eines Teammitglieds\n\n"
                "**Wähle eine Option:**"
            ),
            color=color_int,
        )
        panel_embed.set_footer(text="Support-Team • Wir sind für dich da!", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        
        try:
            await channel.send(embed=panel_embed, view=PanelButtons())
        except discord.Forbidden:
             embed = create_embed("❌ Setup Fehler", f"Keine Berechtigung, Nachrichten/Embeds in {channel.mention} zu senden.", error_color, ctx)
             await ctx.respond(embed=embed, ephemeral=True)
             return
        except discord.HTTPException as e:
             error_message = f"Fehler beim Senden des Panels: {e.status} {e.code} - {e.text}"
             print(error_message)
             embed = create_embed("❌ Setup Fehler", f"Fehler beim Senden des Panels ({e.status}). Überprüfe die Bot-Berechtigungen und Kanal-Einstellungen.", error_color, ctx)
             await ctx.respond(embed=embed, ephemeral=True)
             return
        except Exception as e:
             embed = create_embed("❌ Setup Fehler", f"Unerwarteter Fehler beim Senden des Panels: {e}", error_color, ctx)
             await ctx.respond(embed=embed, ephemeral=True)
             return

        confirm_embed = discord.Embed(
            title="✅ Setup erfolgreich abgeschlossen",
            description=(
                f"### 🎉 Das Ticket-System wurde eingerichtet!\n\n"
                f"📋 **Konfigurationsdetails:**\n"
                f"• **Panel-Kanal:** {channel.mention}\n"
                f"• **Transkript-Archiv:** {transcript_channel.mention}\n"
                f"• **Mitglieder-Rolle:** {member_role.mention}\n"
                f"• **Support-Team Rolle:** {ping_role.mention}\n"
                f"• **Farbschema:** `#{color_int:06x}`"
            ),
            color=success_color,
            timestamp=datetime.datetime.now()
        )
        confirm_embed.set_footer(text=f"{ctx.guild.name} • Ticket-System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)

        config_id = 2104
        data = {
            "category": channel.category.id if channel.category else None,
            "server_id": channel.guild.id,
            "channel": channel.id,
            "transcript_channel": transcript_channel.id,
            "member_role": member_role.id,
            "ping_role": ping_role.id,
            "color": color_int,
        }
        await mongodb.new_config(config_id, data)
        await ctx.respond(embed=confirm_embed, ephemeral=True)


    @tickets_group.command(
        name="find",
        description="Findet ein Ticket-Transkript anhand seiner ID."
    )
    @commands.has_permissions(manage_messages=True)
    async def find(self, ctx: discord.ApplicationContext, ticket_id: int):
        await ctx.defer(ephemeral=True)

        error_color = discord.Color.red()
        info_color = discord.Color.blue()
        warning_color = discord.Color.orange()

        ticket_doc = await mongodb.find_ticket_by_id(ticket_id)

        if not ticket_doc:
            embed = discord.Embed(
                title="❌ Ticket nicht gefunden",
                description=(
                    f"### 🔍 Suchergebnis für Ticket #{ticket_id:04d}\n\n"
                    f"Das Ticket mit der ID `#{ticket_id:04d}` konnte nicht in der Datenbank gefunden werden.\n\n"
                    f"**Mögliche Gründe:**\n"
                    f"• Die Ticket-ID existiert nicht\n"
                    f"• Das Ticket wurde aus der Datenbank gelöscht\n"
                    f"• Es liegt ein Datenbankfehler vor"
                ),
                color=error_color,
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"{ctx.guild.name} • Ticket-System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        config_id = 2104
        config_data = await mongodb.db["config"].find_one({"_id": config_id})
        success_color = discord.Color(config_data.get("color", 0x5865F2)) if config_data else discord.Color.blue()

        if ticket_doc.get("status") != "closed" or not ticket_doc.get("transcript_thread_id"):
            channel_id = ticket_doc.get("channel_id")
            channel_mention = "Unbekannter Kanal"
            if channel_id:
                 channel = ctx.guild.get_channel(channel_id)
                 if channel:
                     channel_mention = channel.mention

            embed = discord.Embed(
                title="ℹ️ Ticket ist noch aktiv",
                description=(
                    f"### 🔍 Suchergebnis für Ticket #{ticket_id:04d}\n\n"
                    f"Das Ticket `#{ticket_id:04d}` ist noch offen oder wurde nicht korrekt archiviert.\n\n"
                    f"**Ticket-Status:** {'🟢 Offen' if ticket_doc.get('status') == 'open' else '⚪ Unbekannt'}\n"
                    f"**Aktueller Kanal:** {channel_mention}"
                ),
                color=warning_color,
                timestamp=datetime.datetime.now()
            )
            embed.set_footer(text=f"{ctx.guild.name} • Ticket-System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
            await ctx.followup.send(embed=embed, ephemeral=True)
            return

        thread_id = ticket_doc["transcript_thread_id"]
        thread = ctx.guild.get_thread(thread_id)

        if not thread:
            try:
                # Versuche, den Thread zu fetchen (falls er archiviert ist)
                thread = await ctx.guild.fetch_channel(thread_id) 
                if not isinstance(thread, discord.Thread):
                    thread = None
            except (discord.NotFound, discord.Forbidden):
                thread = None

            if not thread:
                 embed = discord.Embed(
                    title="❌ Transkript nicht gefunden",
                    description=(
                        f"### 🔍 Suchergebnis für Ticket #{ticket_id:04d}\n\n"
                        f"Das Ticket wurde in der Datenbank gefunden, aber der zugehörige Transkript-Thread "
                        f"(ID: {thread_id}) konnte nicht gefunden werden.\n\n"
                        f"**Mögliche Gründe:**\n"
                        f"• Der Thread wurde manuell gelöscht\n"
                        f"• Der Thread wurde archiviert und ist nicht mehr zugänglich\n"
                        f"• Es liegt ein Berechtigungsproblem vor"
                    ),
                    color=error_color,
                    timestamp=datetime.datetime.now()
                 )
                 embed.set_footer(text=f"{ctx.guild.name} • Ticket-System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
                 await ctx.followup.send(embed=embed, ephemeral=True)
                 return

        # Hole das Datum, wann das Ticket geschlossen wurde (falls gespeichert)
        closed_at_utc = ticket_doc.get('closed_at') # Annahme: Du speicherst das Schließdatum in der DB
        closed_at_str = "Unbekannt"
        if closed_at_utc and isinstance(closed_at_utc, datetime.datetime):
            closed_at_local = closed_at_utc.astimezone(berlin_tz)
            closed_at_str = closed_at_local.strftime('%d.%m.%Y um %H:%M:%S')

        embed = discord.Embed(
            title="🔎 Transkript gefunden",
            description=(
                f"### 📜 Transkript für Ticket #{ticket_id:04d}\n\n"
                f"Das Transkript wurde erfolgreich gefunden!\n\n"
                f"**Details:**\n"
                f"• **Ticket-ID:** `#{ticket_id:04d}`\n"
                f"• **Status:** 🔒 Geschlossen\n"
                f"• **Erstellt von:** <@{ticket_doc.get('user_id', 'Unbekannt')}>\n"
                f"• **Geschlossen am:** {closed_at_str}\n\n" # Verwende das gespeicherte Datum
                f"**Transkript-Thread:** {thread.mention}\n"
                f"**Direkter Link:** [Zum Transkript springen]({thread.jump_url})"
            ),
            color=success_color,
            timestamp=datetime.datetime.now()
        )
        embed.set_footer(text=f"{ctx.guild.name} • Ticket-System", icon_url=ctx.guild.icon.url if ctx.guild.icon else None)
        await ctx.followup.send(embed=embed, ephemeral=True)


    @commands.Cog.listener()
    async def on_ready(self):
        if not getattr(self.bot, 'persistent_views_added', False):
             self.bot.add_view(PanelButtons())
             self.bot.add_view(ConfirmClosingButton())
             self.bot.add_view(TicketEmbedButtons())
             print("✅ Persistent views added successfully.")
             self.bot.persistent_views_added = True


def setup(bot: discord.Bot):
    if not hasattr(bot, 'persistent_views_added'):
        bot.persistent_views_added = False
    bot.add_cog(Tickets(bot))
