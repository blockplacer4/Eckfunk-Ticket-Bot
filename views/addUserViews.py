"""
Discord Ticket Bot - Add User Views Modul

Written in Python by Janosch | blockyy and Luxx

© 2024 Soluslab. All rights reserved.
"""

import discord
import mongodb


class Modal(discord.ui.Modal):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_item(
            discord.ui.InputText(
                label="Welcher User soll hinzugefügt werden? (ID)?",
                placeholder="675779525262573589",
            )
        )

    async def callback(self, interaction):
        user_id = int(self.children[0].value)
        user = await interaction.guild.fetch_member(user_id)
        if not user:
            embed = discord.Embed(
                title="Fehler!",
                description=(
                    "Dieser User konnte nicht hinzugefügt werden, vielleicht die falsche ID?"
                ),
                color=0xff5252,
            )
            await interaction.respond(embed=embed)
            return
        await interaction.channel.set_permissions(
            user,
            send_messages=True,
            view_channel=True,
            read_message_history=True,
            attach_files=True,
        )
        embed = discord.Embed(
            title="User hinzugefügt!",
            description=f"Der User {user.mention} wurde erfolgreich hinzugefügt!",
            color=0xff5252,
        )
        await interaction.respond(user.mention, embed=embed)


def setup(bot: discord.Bot):
    pass  # Dieser Modal wird direkt über den Button im Ticket-Embed aufgerufen.
