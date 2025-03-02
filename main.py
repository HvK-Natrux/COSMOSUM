
import os
import discord
from discord.ext import commands
from discord import app_commands
import json
from faction_manager import FactionManager

# Configuration du bot avec les intents nécessaires
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents, application_commands=False)
faction_manager = FactionManager()

# Boutons pour Créer une Faction et Rejoindre une Faction
class BoutonsFaction(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Créer une Faction", style=discord.ButtonStyle.green, custom_id="create_faction")
    async def creer_faction(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalCreationFaction()
        await interaction.response.send_modal(modal)

    @discord.ui.button(label="Rejoindre une Faction", style=discord.ButtonStyle.primary, custom_id="join_faction")
    async def rejoindre_faction(self, interaction: discord.Interaction, button: discord.ui.Button):
        modal = ModalRejoindreFacton()
        await interaction.response.send_modal(modal)

class ModalCreationFaction(discord.ui.Modal, title="Créer une Faction"):
    nom_faction = discord.ui.TextInput(
        label="Nom de la Faction",
        placeholder="Entrer le nom de la faction...",
        min_length=3,
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):
        nom = self.nom_faction.value.strip()
        try:
            resultat = await faction_manager.create_faction(interaction, nom)
            await interaction.response.send_message(resultat, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur: {str(e)}", ephemeral=True)

class ModalRejoindreFacton(discord.ui.Modal, title="Rejoindre une Faction"):
    nom_faction = discord.ui.TextInput(
        label="Nom de la Faction",
        placeholder="Entrer le nom de la faction à rejoindre...",
        min_length=3,
        max_length=32
    )

    async def on_submit(self, interaction: discord.Interaction):
        nom = self.nom_faction.value.strip()
        try:
            resultat = await faction_manager.join_faction(interaction, nom)
            await interaction.response.send_message(resultat, ephemeral=True)
        except Exception as e:
            await interaction.response.send_message(f"❌ Erreur: {str(e)}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Bot est prêt ! Connecté en tant que {bot.user}")
    try:
        bot.add_view(BoutonsFaction())
        print("Boutons de faction enregistrés avec succès")
    except Exception as e:
        print(f"Erreur lors de la configuration des vues: {e}")

@bot.command()
@commands.has_permissions(administrator=True)
async def configchoix(ctx):
    """Configure le canal de choix de faction"""
    try:
        embed = discord.Embed(
            title="🏰 Système de Faction",
            description="Choisissez de créer ou rejoindre une faction:\n\n"
                       "• Cliquez sur **Créer une Faction** pour démarrer votre propre faction\n"
                       "• Cliquez sur **Rejoindre une Faction** pour rejoindre une faction existante",
            color=discord.Color.blue()
        )

        view = BoutonsFaction()
        await ctx.send(embed=embed, view=view)
    except Exception as e:
        await ctx.send(f"❌ Erreur lors de la configuration du système de faction: {str(e)}")

@configchoix.error
async def configchoix_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("❌ Vous avez besoin des permissions d'administrateur pour utiliser cette commande !")
    else:
        await ctx.send(f"❌ Une erreur s'est produite: {str(error)}")

# Exécution du bot avec le token depuis la variable d'environnement
bot.run(os.getenv('DISCORD_TOKEN'))
