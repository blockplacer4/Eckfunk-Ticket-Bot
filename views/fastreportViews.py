"""
Discord Ticket Bot - Fast Report Views Modul

Written in Python by Janosch | blockyy and Luxx

© 2024 Soluslab. All rights reserved.
"""

import asyncio
import datetime
import discord
import mongodb
from cogs import tickets


class Modal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(label="Kategorisiere dein Anliegen...")
        )
        self.add_item(
            discord.ui.InputText(
                label="Erkläre uns dein Anliegen...", style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Links zu Beweisen und anderem...",
                style=discord.InputTextStyle.long
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Welche User sind involviert? (bitte User IDs)",
                placeholder="675779525262573589, 858011419760132137",
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Entscheidungen werden akzeptiert, verstanden?",
                placeholder="Ja!",
            )
        )

    async def callback(self, interaction):
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="⮞ Bitte hab einen kurzen Moment Geduld, das Ticket wird gerade geöffnet… ⮞",
            color=0xff5252,
        )
        await interaction.respond(embed=embed, ephemeral=True)
        await interaction.edit(content=None, embed=embed)
        await asyncio.sleep(0.4)
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="🔍 Die richtige Kategorie wird in der Datenbank gesucht… 🔍",
            color=0xff5252,
        )
        await asyncio.sleep(0.4)
        await interaction.edit(content=None, embed=embed)
        ticket_id = await mongodb.get_new_ticket_id()
        channel_id = await mongodb.get_data("config", 2104, "channel")
        channel = await interaction.guild.fetch_channel(channel_id)
        category_id = await mongodb.get_data("config", 2104, "category")
        category = discord.utils.get(interaction.guild.categories, id=category_id)
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="🎯 Der Channel wird erstellt… 🎯",
            color=0xff5252,
        )
        await interaction.edit(content=None, embed=embed)
        await asyncio.sleep(0.7)
        created_channel = await interaction.guild.create_text_channel(
            name=f"report-{interaction.user.name}-{'{:04d}'.format(ticket_id)}",
            category=category,
            position=channel.position,
        )
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="👀 Die Permissions werden gesetzt… 👀",
            color=0xff5252,
        )
        await interaction.edit(content=None, embed=embed)
        await created_channel.set_permissions(
            interaction.guild.default_role, view_channel=False
        )
        await created_channel.set_permissions(
            interaction.user,
            send_messages=True,
            view_channel=True,
            read_message_history=True,
            attach_files=True,
        )
        member_role = await mongodb.get_data("config", 2104, "member_role")
        await created_channel.set_permissions(
            interaction.guild.get_role(member_role),
            send_messages=False,
            view_channel=False,
            read_message_history=False,
            attach_files=False,
        )
        ping_role = await mongodb.get_data("config", 2104, "ping_role")
        await created_channel.set_permissions(
            interaction.guild.get_role(ping_role),
            send_messages=True,
            view_channel=True,
            read_message_history=True,
            attach_files=True,
        )
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="🔧 Das Embed wird ins Ticket gesendet… 🔧",
            color=0xff5252,
        )
        await interaction.edit(content=None, embed=embed)
        await asyncio.sleep(0.4)
        embed = discord.Embed(
            title="Report Ticket",
            color=0xff5252,
            timestamp=datetime.datetime.now(),
            description=(
                "Wir bitten um dein Verständnis, wenn unsere Teammitglieder manchmal "
                "etwas länger für eine Antwort brauchen."
            ),
        )
        embed.add_field(name="Status", value="Open")
        embed.add_field(
            name="Kategorie", value=self.children[0].value, inline=False
        )
        embed.add_field(
            name="Genauere Beschreibung",
            value=self.children[1].value,
            inline=False,
        )
        embed.add_field(
            name="Beweise", value=self.children[2].value, inline=False
        )
        embed.add_field(
            name="Involvierte User",
            value=self.children[3].value,
            inline=False,
        )
        embed.add_field(
            name="Entscheidungen werden akzeptiert, verstanden?",
            value=self.children[4].value,
            inline=False,
        )
        ping_role = await mongodb.get_data("config", 2104, "ping_role")
        message_obj = await created_channel.send(
            f"<@&{ping_role}> {interaction.user.mention}",
            embed=embed,
            view=tickets.TicketEmbedButtons(),
        )
        await mongodb.insert_new_ticket(
            ticket_id,
            interaction.user.id,
            "support",
            datetime.datetime.now(),
            created_channel.id,
            "open",
            message_obj.id,
        )
        embed = discord.Embed(
            title="Ticket erstellt",
            description=f"Dein Ticket wurde erfolgreich erstellt \n\n {message_obj.jump_url}",
            colour=0xff5252,
            timestamp=datetime.datetime.now(),
        )
        await interaction.edit(content=None, embed=embed, delete_after=15)


def setup(bot: discord.Bot):
    pass  # Dieser Modal wird direkt über den Button aufgerufen.
