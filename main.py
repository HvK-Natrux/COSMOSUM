import os
import discord
from discord.ext import commands
from discord import app_commands
import json
from faction_manager import FactionManager
from web_app import start_server
from keep_alive import keep_alive

# Configuration du bot avec les intents nécessaires
intents = discord.Intents.default()
intents.message_content = True
intents.members = True

bot = commands.Bot(command_prefix="!", intents=intents)
faction_manager = FactionManager()

# Démarrage des deux serveurs web avant le bot
print("Démarrage de l'interface web principale...")
start_server()
print("Interface web principale démarrée sur http://0.0.0.0:5000")

print("Démarrage du serveur keep_alive...")
keep_alive()
print("Serveur keep_alive démarré sur http://0.0.0.0:8080")

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
        print(f"Erreur lors de la configuration: {e}")

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

@bot.command()
async def taux(ctx, taux: float):
    """Définit le taux de change de votre faction (1 unité = X monnaie générale)"""
    try:
        result = await faction_manager.set_exchange_rate(ctx.interaction, taux)
        await ctx.send(f"✅ {result}")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
@commands.has_permissions(administrator=True)
async def ajouter(ctx, faction: str, montant: int):
    """[Admin] Ajoute de la monnaie à une faction"""
    try:
        result = await faction_manager.add_currency(ctx.interaction, faction, montant)
        await ctx.send(f"✅ {result}")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def transferer(ctx, faction: str, montant: int):
    """Transfère de la monnaie à une autre faction selon les taux de change"""
    try:
        result = await faction_manager.transfer_currency(ctx.interaction, faction, montant)
        await ctx.send(f"✅ {result}")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def solde(ctx):
    """Affiche le solde de votre faction"""
    try:
        factions = faction_manager._load_factions()
        user_faction = None
        
        for faction_name, faction_data in factions.items():
            role = ctx.guild.get_role(faction_data["role_id"])
            if role and role in ctx.author.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            await ctx.send("❌ Vous n'êtes pas membre d'une faction !")
            return
            
        faction_data = factions[user_faction]
        await ctx.send(f"💰 Faction '{user_faction}': {faction_data['balance']} {faction_data['currency_name']} (Taux de change: 1 {faction_data['currency_name']} = {faction_data['exchange_rate']} monnaie générale)")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def ressources(ctx):
    """Affiche les ressources de votre faction"""
    try:
        resources = await faction_manager.get_resources(ctx.interaction)
        
        embed = discord.Embed(
            title="📦 Ressources de votre faction",
            color=discord.Color.green()
        )
        
        for resource, amount in resources.items():
            emoji = "🪵" if resource == "bois" else "🪨" if resource == "pierre" else "⛓️" if resource == "fer" else "🪙"
            embed.add_field(name=f"{emoji} {resource.capitalize()}", value=str(amount), inline=True)
            
        await ctx.send(embed=embed)
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
@commands.has_permissions(administrator=True)
async def ajouterressource(ctx, faction: str, ressource: str, montant: int):
    """[Admin] Ajoute des ressources à une faction"""
    try:
        # Pour les admins, on ajoute directement à la faction spécifiée
        factions = faction_manager._load_factions()
        
        if faction not in factions:
            await ctx.send(f"❌ La faction '{faction}' n'existe pas !")
            return
            
        valid_resources = ["bois", "pierre", "fer", "or"]
        if ressource not in valid_resources:
            await ctx.send(f"❌ Ressource invalide ! Les ressources disponibles sont: {', '.join(valid_resources)}")
            return
            
        factions[faction]["resources"][ressource] += montant
        faction_manager._save_factions(factions)
        
        await ctx.send(f"✅ {montant} {ressource} ajoutés à la faction '{faction}' !")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def batiments(ctx):
    """Affiche les bâtiments de votre faction"""
    try:
        factions = faction_manager._load_factions()
        user_faction = None
        
        for faction_name, faction_data in factions.items():
            role = ctx.guild.get_role(faction_data["role_id"])
            if role and role in ctx.author.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            await ctx.send("❌ Vous n'êtes pas membre d'une faction !")
            return
            
        faction_buildings = factions[user_faction].get("buildings", {})
        available_buildings = faction_manager.get_available_buildings()
        
        if not faction_buildings:
            await ctx.send("📦 Votre faction n'a pas encore construit de bâtiments.")
            return
            
        embed = discord.Embed(
            title=f"🏗️ Bâtiments de la faction '{user_faction}'",
            color=discord.Color.blue()
        )
        
        for building_name, level in faction_buildings.items():
            building_info = available_buildings[building_name]
            level_info = building_info["niveaux"][level]
            embed.add_field(
                name=f"{building_info['nom']} (Niveau {level})",
                value=f"**Description:** {building_info['description']}\n**Bonus actuel:** {level_info['bonus']}",
                inline=False
            )
            
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def construire(ctx, batiment: str):
    """Construit ou améliore un bâtiment pour votre faction"""
    try:
        result = await faction_manager.build(ctx.interaction, batiment)
        await ctx.send(f"✅ {result}")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def batimentsdispo(ctx):
    """Affiche les bâtiments disponibles à la construction"""
    try:
        available_buildings = faction_manager.get_available_buildings()
        
        embed = discord.Embed(
            title="🏗️ Bâtiments disponibles",
            description="Liste des bâtiments que vous pouvez construire pour votre faction",
            color=discord.Color.gold()
        )
        
        for building_id, building_info in available_buildings.items():
            # Créer une description avec les coûts pour chaque niveau
            description = f"**{building_info['description']}**\n\n"
            
            for level, level_info in building_info["niveaux"].items():
                costs = ", ".join([f"{amount} {resource}" for resource, amount in level_info["cout"].items()])
                description += f"**Niveau {level}:** {costs}\n*Bonus:* {level_info['bonus']}\n\n"
                
            embed.add_field(
                name=f"{building_info['nom']} (`{building_id}`)",
                value=description,
                inline=False
            )
            
        await ctx.send(embed=embed)
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

@bot.command()
async def transfererressource(ctx, faction: str, ressource: str, montant: int):
    """Transfère des ressources à une autre faction"""
    try:
        result = await faction_manager.transfer_resource(ctx.interaction, faction, ressource, montant)
        await ctx.send(f"✅ {result}")
    except ValueError as e:
        await ctx.send(f"❌ {str(e)}")
    except Exception as e:
        await ctx.send(f"❌ Une erreur s'est produite: {str(e)}")

# Exécution du bot avec le token depuis la variable d'environnement
bot.run(os.getenv('DISCORD_TOKEN'))
