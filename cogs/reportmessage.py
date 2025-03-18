"""
Discord Ticket Bot - Report Message Modul

Written in Python by Janosch | blockyy and Luxx

© 2024 Soluslab. All rights reserved.
"""

import asyncio
import datetime
import discord
from discord.ext import commands

import mongodb
from cogs import tickets


class Modal(discord.ui.Modal):
    def __init__(self, ctx, message, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.context = ctx
        self.message = message
        self.add_item(
            discord.ui.InputText(
                label="Welche User sind noch beteiligt?",
                placeholder="Bitte immer mit einem Leerzeichen trennen",
            )
        )
        self.add_item(
            discord.ui.InputText(
                label="Weiterer benötigter Kontext...",
                placeholder="Kontext für die Verständlichkeit des Reports",
                style=discord.InputTextStyle.long,
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
        await interaction.edit(content=None, embed=embed)
        ticket_id = await mongodb.get_new_ticket_id()
        channel_id = await mongodb.get_data("config", 2104, "channel")
        channel = await self.message.guild.fetch_channel(channel_id)
        category_id = await mongodb.get_data("config", 2104, "category")
        category = discord.utils.get(self.message.guild.categories, id=category_id)
        embed = discord.Embed(
            title="Dein Ticket wird geöffnet...",
            description="🎯 Der Channel wird erstellt… 🎯",
            color=0xff5252,
        )
        await interaction.edit(content=None, embed=embed)
        await asyncio.sleep(0.6)
        created_channel = await self.message.guild.create_text_channel(
            name=f"report-{self.context.user.name}-{'{:04d}'.format(ticket_id)}",
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
            self.context.user,
            view_channel=True,
            send_messages=True,
            read_message_history=True,
            attach_files=True,
        )
        member_role = await mongodb.get_data("config", 2104, "member_role")
        await created_channel.set_permissions(
            self.message.guild.get_role(member_role),
            send_messages=False,
            view_channel=False,
            read_message_history=False,
            attach_files=False,
        )
        ping_role = await mongodb.get_data("config", 2104, "ping_role")
        await created_channel.set_permissions(
            self.message.guild.get_role(ping_role),
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
        embed.add_field(name="Kategorie", value="Message Report", inline=False)
        embed.add_field(
            name="Reported Message",
            value=f'"{self.message.content}" von {self.message.author.mention}',
            inline=False,
        )
        embed.add_field(
            name="Weitere Involvierte User", value=self.children[0].value, inline=False
        )
        embed.add_field(
            name="Weiterer Kontext...", value=self.children[1].value, inline=False
        )
        ping_role = await mongodb.get_data("config", 2104, "ping_role")
        message_obj = await created_channel.send(
            f"<@&{ping_role}> {self.context.user.mention}",
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


class ReportMessage(commands.Cog):
    def __init__(self, bot: discord.Bot):
        self.bot = bot

    @commands.message_command(name="Report Message")
    async def report_message(self, ctx, message: discord.Message):
        modal = Modal(ctx=ctx, message=message, title="Report Message")
        await ctx.send_modal(modal)


def setup(bot: discord.Bot):
    bot.add_cog(ReportMessage(bot))
