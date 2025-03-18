"""
Discord Ticket Bot - Tickets Modul

Written in Python by Janosch | blockyy and Luxx

© 2024 Soluslab. All rights reserved.
"""

import datetime
import discord
from discord.ext import commands

import mongodb
from views import (
    supportViews,
    fastreportViews,
    partyBewerbungViews,
    addUserViews,
)


class PanelButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.success,
        label="Support",
        emoji="🛠️",
        custom_id="support-button",
    )
    async def support_callback(self, button, interaction):
        modal = supportViews.Modal(title="Support Ticket")
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        label="Fast Report",
        emoji="⚡",
        custom_id="fastreport-button",
    )
    async def fastreport_callback(self, button, interaction):
        modal = fastreportViews.Modal(title="Fast Report")
        await interaction.response.send_modal(modal)

    @discord.ui.button(
        style=discord.ButtonStyle.secondary,
        label="Partei Bewerbung",
        emoji="🏛️",
        custom_id="partei-bewerbung-button",
    )
    async def partei_bewerbung_callback(self, button, interaction):
        modal = partyBewerbungViews.Modal(title="Partei Bewerbungs Ticket")
        await interaction.response.send_modal(modal)


class TicketEmbedButtons(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.red,
        label="Schließen",
        emoji="🔒",
        custom_id="closing-button",
    )
    async def close_callback(self, button, interaction):
        embed = discord.Embed(
            title="Bestätigung",
            description="Soll das Ticket wirklich geschlossen werden?",
            timestamp=datetime.datetime.now(),
            color=0xff5252,
        )
        embed.set_author(name=interaction.user.name)
        await interaction.response.send_message(embed=embed, view=ConfirmClosingButton())

    @discord.ui.button(
        style=discord.ButtonStyle.primary,
        label="Add User",
        emoji="➕",
        custom_id="add-user-button",
    )
    async def add_button(self, button, interaction):
        modal = addUserViews.Modal(title="User Hinzufügen")
        await interaction.response.send_modal(modal)


class ConfirmClosingButton(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        style=discord.ButtonStyle.green,
        label="Confirm",
        custom_id="confirm-closing-button",
    )
    async def close_button_callback(self, button, interaction):
        embed = discord.Embed(
            title="Ticket geschlossen",
            description="Das Ticket wurde geschlossen!",
            color=0xff5252,
        )
        await interaction.respond(embed=embed)
        deleted_category_id = await mongodb.get_data("config", 2104, "deleted_ticket_category")
        category = discord.utils.get(interaction.guild.categories, id=deleted_category_id)
        await interaction.channel.edit(category=category, sync_permissions=True)


class Tickets(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.slash_command(
        guilds=[1262092154147438643]
    )
    @commands.has_permissions(administrator=True)
    async def setup(
        self,
        ctx,
        channel: discord.TextChannel,
        deleted_tickets_category: discord.CategoryChannel,
        member_role: discord.Role,
        ping_role: discord.Role,
        color: int,
    ):
        embed = discord.Embed(
            title="Ticket Support",
            description=(
                "Willkommen beim Ticket Support!\n\n"
                "Unser System ermöglicht dir eine schnelle und einfache Möglichkeit, "
                "Unterstützung für deine Anliegen zu erhalten.\n\n"
                "Wähle eine der folgenden Optionen, um ein Ticket zu eröffnen und "
                "unser Team wird dir so schnell wie möglich helfen."
            ),
            color=color,
        )
        await channel.send(embed=embed, view=PanelButtons())
        confirm_embed = discord.Embed(
            title="Ticket Panel erstellt",
            description="Das Ticket Panel wurde erfolgreich in den Channel gesendet",
            color=color,
        )
        await ctx.respond(embed=confirm_embed, ephemeral=True, delete_after=30)
        data = {
            "category": channel.category.id,
            "server_id": channel.guild.id,
            "channel": channel.id,
            "deleted_ticket_category": deleted_tickets_category.id,
            "member_role": member_role.id,
            "ping_role": ping_role.id,
            "color": color,
        }
        await mongodb.new_config(2104, data)

    @commands.Cog.listener()
    async def on_ready(self):
        self.bot.add_view(PanelButtons())
        self.bot.add_view(ConfirmClosingButton())
        self.bot.add_view(TicketEmbedButtons())


def setup(bot: discord.Bot):
    bot.add_cog(Tickets(bot))
