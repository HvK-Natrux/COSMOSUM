
import discord
import json
import os
from typing import Dict, Optional

class FactionManager:
    def __init__(self, filename: str = "data/factions.json"):
        self.filename = filename
        self._ensure_data_file()

    def _ensure_data_file(self):
        """Assure que le fichier de données des factions existe"""
        os.makedirs(os.path.dirname(self.filename), exist_ok=True)
        if not os.path.exists(self.filename):
            with open(self.filename, 'w') as f:
                json.dump({}, f)

    def _load_factions(self) -> Dict:
        """Charge les données des factions depuis le fichier JSON"""
        try:
            with open(self.filename, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Erreur lors du chargement des factions: {e}")
            return {}

    def _save_factions(self, data: Dict):
        """Enregistre les données des factions dans le fichier JSON"""
        try:
            with open(self.filename, 'w') as f:
                json.dump(data, f, indent=4)
        except Exception as e:
            print(f"Erreur lors de l'enregistrement des factions: {e}")
            raise

    async def _check_bot_permissions(self, interaction: discord.Interaction):
        """Vérifie si le bot a les permissions nécessaires"""
        bot_member = interaction.guild.me
        required_permissions = [
            "manage_roles",
            "manage_channels",
            "read_messages",
            "send_messages"
        ]

        missing_permissions = []
        for perm in required_permissions:
            if not getattr(bot_member.guild_permissions, perm):
                missing_permissions.append(perm)

        if missing_permissions:
            raise ValueError(f"Le bot manque des permissions requises: {', '.join(missing_permissions)}")

    async def create_faction(self, interaction: discord.Interaction, faction_name: str):
        """Crée une nouvelle faction avec rôle et canaux associés"""
        # Vérifie d'abord les permissions du bot
        await self._check_bot_permissions(interaction)

        # Charge les factions actuelles
        factions = self._load_factions()

        # Vérifie si la faction existe déjà
        if faction_name in factions:
            raise ValueError("Une faction avec ce nom existe déjà !")

        # Crée le rôle
        try:
            role = await interaction.guild.create_role(
                name=faction_name,
                reason="Création de Faction",
                color=discord.Color.random()  # Couleur aléatoire pour distinction visuelle
            )

            # Crée la catégorie avec les permissions appropriées
            overwrites = {
                interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
                role: discord.PermissionOverwrite(read_messages=True, send_messages=True),
                interaction.guild.me: discord.PermissionOverwrite(read_messages=True, send_messages=True)
            }

            category = await interaction.guild.create_category(
                name=faction_name,
                overwrites=overwrites
            )

            # Crée les canaux textuels et vocaux
            text_channel = await category.create_text_channel(f"{faction_name.lower()}-discussion")
            voice_channel = await category.create_voice_channel(f"{faction_name.lower()}-vocal")

            # Ajoute le rôle au membre
            await interaction.user.add_roles(role)

            # Enregistre les données de la faction
            factions[faction_name] = {
                "leader": interaction.user.id,
                "balance": 0,
                "currency_name": f"{faction_name}Coin",
                "exchange_rate": 1,  # Taux par défaut: 1 = 1 monnaie générale
                "role_id": role.id,
                "category_id": category.id,
                "text_channel_id": text_channel.id,
                "voice_channel_id": voice_channel.id,
                "resources": {
                    "bois": 100,
                    "pierre": 50,
                    "fer": 20,
                    "or": 5
                },
                "buildings": {}
            }
            self._save_factions(factions)

            return f"Faction '{faction_name}' créée avec succès avec des canaux et un rôle dédiés !"

        except discord.Forbidden:
            # Nettoyage en cas d'échec
            if 'role' in locals():
                await role.delete()
            if 'category' in locals():
                await category.delete()
            raise ValueError("Le bot n'a pas les permissions requises pour créer des factions !")
        except Exception as e:
            # Nettoyage en cas d'échec
            if 'role' in locals():
                await role.delete()
            if 'category' in locals():
                await category.delete()
            raise Exception(f"Échec de la création de faction: {str(e)}")

    async def join_faction(self, interaction: discord.Interaction, faction_name: str):
        """Permet à un utilisateur de rejoindre une faction existante"""
        # Vérifie d'abord les permissions du bot
        await self._check_bot_permissions(interaction)

        factions = self._load_factions()

        if faction_name not in factions:
            raise ValueError("Cette faction n'existe pas !")

        # Vérifie si l'utilisateur est déjà dans une faction
        member_roles = [role.name for role in interaction.user.roles]
        for faction in factions.keys():
            if faction in member_roles:
                raise ValueError("Vous êtes déjà dans une faction !")

        # Ajoute l'utilisateur à la faction
        role = interaction.guild.get_role(factions[faction_name]["role_id"])
        if not role:
            raise ValueError("Rôle de faction non trouvé !")

        try:
            await interaction.user.add_roles(role)
            return f"Faction '{faction_name}' rejointe avec succès !"
        except discord.Forbidden:
            raise ValueError("Le bot n'a pas la permission d'attribuer des rôles !")
            
    async def set_exchange_rate(self, interaction: discord.Interaction, rate: float):
        """Définit le taux de change de la faction de l'utilisateur"""
        # Vérifie que l'utilisateur est dans une faction et qu'il en est le chef
        factions = self._load_factions()
        user_faction = None
        
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
            
        # Vérifie que l'utilisateur est le chef de la faction
        if factions[user_faction]["leader"] != interaction.user.id:
            raise ValueError("Seul le chef de faction peut modifier le taux de change !")
            
        # Vérifie que le taux est positif
        if rate <= 0:
            raise ValueError("Le taux de change doit être un nombre positif !")
            
        # Met à jour le taux de change
        factions[user_faction]["exchange_rate"] = rate
        self._save_factions(factions)
        
        return f"Taux de change de '{user_faction}' modifié avec succès ! 1 {factions[user_faction]['currency_name']} = {rate} monnaie générale"
        
    async def add_currency(self, interaction: discord.Interaction, faction_name: str, amount: int):
        """Ajoute de la monnaie à une faction (commande admin)"""
        if not interaction.user.guild_permissions.administrator:
            raise ValueError("Cette commande est réservée aux administrateurs !")
            
        factions = self._load_factions()
        
        if faction_name not in factions:
            raise ValueError(f"La faction '{faction_name}' n'existe pas !")
            
        factions[faction_name]["balance"] += amount
        self._save_factions(factions)
        
        return f"{amount} {factions[faction_name]['currency_name']} ajoutés à la faction '{faction_name}' !"
        
    async def transfer_currency(self, interaction: discord.Interaction, target_faction: str, amount: int):
        """Transfère de la monnaie entre factions selon les taux de change"""
        factions = self._load_factions()
        
        # Trouve la faction de l'utilisateur
        source_faction = None
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                source_faction = faction_name
                break
                
        if not source_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
            
        if target_faction not in factions:
            raise ValueError(f"La faction cible '{target_faction}' n'existe pas !")
            
        if source_faction == target_faction:
            raise ValueError("Vous ne pouvez pas transférer vers votre propre faction !")
            
        # Vérifie que l'utilisateur a assez de monnaie
        if factions[source_faction]["balance"] < amount:
            raise ValueError(f"Solde insuffisant ! Vous avez {factions[source_faction]['balance']} {factions[source_faction]['currency_name']}")
            
        # Calcul du montant converti selon les taux de change
        source_rate = factions[source_faction]["exchange_rate"]  # Taux source -> monnaie générale
        target_rate = factions[target_faction]["exchange_rate"]  # Taux cible -> monnaie générale
        
        # Conversion: montant en monnaie source -> monnaie générale -> monnaie cible
        general_currency = amount * source_rate
        converted_amount = int(general_currency / target_rate)
        
        # Effectue le transfert
        factions[source_faction]["balance"] -= amount
        factions[target_faction]["balance"] += converted_amount
        self._save_factions(factions)
        
        return f"Transfert réussi ! Vous avez envoyé {amount} {factions[source_faction]['currency_name']} à '{target_faction}', qui a reçu {converted_amount} {factions[target_faction]['currency_name']}"
        
    async def get_resources(self, interaction: discord.Interaction):
        """Affiche les ressources de la faction de l'utilisateur"""
        factions = self._load_factions()
        
        # Trouve la faction de l'utilisateur
        user_faction = None
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
            
        return factions[user_faction]["resources"]
    
    async def add_resource(self, interaction: discord.Interaction, resource_name: str, amount: int):
        """Ajoute une ressource à la faction (commande admin)"""
        if not interaction.user.guild_permissions.administrator:
            raise ValueError("Cette commande est réservée aux administrateurs !")
            
        # Vérifie que la ressource existe
        valid_resources = ["bois", "pierre", "fer", "or"]
        if resource_name not in valid_resources:
            raise ValueError(f"Ressource invalide ! Les ressources disponibles sont: {', '.join(valid_resources)}")
        
        factions = self._load_factions()
        
        # Trouve la faction de l'utilisateur
        user_faction = None
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
        
        # Ajoute la ressource
        factions[user_faction]["resources"][resource_name] += amount
        self._save_factions(factions)
        
        return f"{amount} {resource_name} ajoutés à votre faction !"
    
    def get_available_buildings(self):
        """Renvoie la liste des bâtiments disponibles à la construction"""
        return {
            "quartier_general": {
                "nom": "Quartier Général",
                "description": "Centre de commandement de la faction",
                "niveaux": {
                    1: {"cout": {"bois": 100, "pierre": 50}, "bonus": "Débloque la construction d'autres bâtiments"},
                    2: {"cout": {"bois": 200, "pierre": 100, "fer": 20}, "bonus": "+10% de production de ressources"},
                    3: {"cout": {"bois": 400, "pierre": 200, "fer": 50, "or": 10}, "bonus": "+25% de production de ressources"}
                }
            },
            "mine": {
                "nom": "Mine",
                "description": "Produit de la pierre et du fer",
                "niveaux": {
                    1: {"cout": {"bois": 50, "pierre": 30}, "bonus": "Production: +5 pierre par jour"},
                    2: {"cout": {"bois": 100, "pierre": 60, "fer": 10}, "bonus": "Production: +10 pierre, +3 fer par jour"},
                    3: {"cout": {"bois": 200, "pierre": 120, "fer": 30, "or": 5}, "bonus": "Production: +20 pierre, +8 fer, +1 or par jour"}
                }
            },
            "scierie": {
                "nom": "Scierie",
                "description": "Produit du bois",
                "niveaux": {
                    1: {"cout": {"bois": 30, "pierre": 50}, "bonus": "Production: +10 bois par jour"},
                    2: {"cout": {"bois": 60, "pierre": 100, "fer": 10}, "bonus": "Production: +25 bois par jour"},
                    3: {"cout": {"bois": 120, "pierre": 200, "fer": 30, "or": 5}, "bonus": "Production: +60 bois par jour"}
                }
            },
            "forge": {
                "nom": "Forge",
                "description": "Améliore l'efficacité des ressources",
                "niveaux": {
                    1: {"cout": {"bois": 80, "pierre": 100, "fer": 30}, "bonus": "+5% d'efficacité des ressources"},
                    2: {"cout": {"bois": 160, "pierre": 200, "fer": 60, "or": 5}, "bonus": "+15% d'efficacité des ressources"},
                    3: {"cout": {"bois": 320, "pierre": 400, "fer": 120, "or": 15}, "bonus": "+30% d'efficacité des ressources"}
                }
            },
            "marche": {
                "nom": "Marché",
                "description": "Améliore les échanges entre factions",
                "niveaux": {
                    1: {"cout": {"bois": 150, "pierre": 100, "fer": 20}, "bonus": "+5% sur les taux d'échange"},
                    2: {"cout": {"bois": 300, "pierre": 200, "fer": 40, "or": 10}, "bonus": "+15% sur les taux d'échange"},
                    3: {"cout": {"bois": 600, "pierre": 400, "fer": 80, "or": 25}, "bonus": "+30% sur les taux d'échange"}
                }
            },
            # Nouveaux bâtiments administratifs
            "palais": {
                "nom": "Palais",
                "description": "Centre administratif et politique de la faction",
                "niveaux": {
                    1: {"cout": {"bois": 200, "pierre": 150, "fer": 40}, "bonus": "+5% de diplomatie avec autres factions"},
                    2: {"cout": {"bois": 400, "pierre": 300, "fer": 80, "or": 15}, "bonus": "+15% de diplomatie, débloque les alliances"},
                    3: {"cout": {"bois": 800, "pierre": 600, "fer": 160, "or": 40}, "bonus": "+30% de diplomatie, permet de créer des pactes commerciaux"}
                }
            },
            "academie": {
                "nom": "Académie",
                "description": "Centre de recherche et de développement",
                "niveaux": {
                    1: {"cout": {"bois": 180, "pierre": 180, "fer": 30}, "bonus": "Débloque 2 technologies de base"},
                    2: {"cout": {"bois": 360, "pierre": 360, "fer": 60, "or": 10}, "bonus": "Débloque 3 technologies avancées"},
                    3: {"cout": {"bois": 720, "pierre": 720, "fer": 120, "or": 30}, "bonus": "Débloque les technologies de prestige"}
                }
            },
            "tresorerie": {
                "nom": "Trésorerie",
                "description": "Sécurise et augmente les finances de la faction",
                "niveaux": {
                    1: {"cout": {"bois": 100, "pierre": 200, "fer": 50}, "bonus": "+10% de revenus quotidiens"},
                    2: {"cout": {"bois": 200, "pierre": 400, "fer": 100, "or": 20}, "bonus": "+25% de revenus quotidiens, +5% d'intérêts"},
                    3: {"cout": {"bois": 400, "pierre": 800, "fer": 200, "or": 50}, "bonus": "+50% de revenus quotidiens, +15% d'intérêts"}
                }
            },
            "tribunal": {
                "nom": "Tribunal",
                "description": "Gère les lois et la justice de la faction",
                "niveaux": {
                    1: {"cout": {"bois": 150, "pierre": 150, "fer": 20}, "bonus": "Permet de créer 3 lois internes"},
                    2: {"cout": {"bois": 300, "pierre": 300, "fer": 40, "or": 10}, "bonus": "Permet de créer 6 lois internes, améliore la stabilité"},
                    3: {"cout": {"bois": 600, "pierre": 600, "fer": 80, "or": 25}, "bonus": "Permet de créer 10 lois, influence les autres factions"}
                }
            },
            "ambassade": {
                "nom": "Ambassade",
                "description": "Améliore les relations diplomatiques",
                "niveaux": {
                    1: {"cout": {"bois": 120, "pierre": 180, "fer": 30}, "bonus": "Permet d'envoyer 1 ambassadeur"},
                    2: {"cout": {"bois": 240, "pierre": 360, "fer": 60, "or": 15}, "bonus": "Permet d'envoyer 3 ambassadeurs, +10% de relations"},
                    3: {"cout": {"bois": 480, "pierre": 720, "fer": 120, "or": 35}, "bonus": "Permet d'envoyer 5 ambassadeurs, +25% de relations"}
                }
            }
        }
    
    async def build(self, interaction: discord.Interaction, building_name: str):
        """Construit ou améliore un bâtiment pour la faction"""
        buildings = self.get_available_buildings()
        
        # Vérifie que le bâtiment existe
        if building_name not in buildings:
            raise ValueError(f"Bâtiment invalide ! Les bâtiments disponibles sont: {', '.join(buildings.keys())}")
        
        factions = self._load_factions()
        
        # Trouve la faction de l'utilisateur
        user_faction = None
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                user_faction = faction_name
                break
                
        if not user_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
            
        # Vérifie que l'utilisateur est le chef de la faction
        if factions[user_faction]["leader"] != interaction.user.id:
            raise ValueError("Seul le chef de faction peut construire des bâtiments !")
            
        # Vérifie si le bâtiment existe déjà et obtient le niveau actuel
        faction_buildings = factions[user_faction].get("buildings", {})
        current_level = faction_buildings.get(building_name, 0)
        
        # Vérifie si le niveau suivant existe
        if current_level + 1 not in buildings[building_name]["niveaux"]:
            raise ValueError(f"Niveau maximum atteint pour ce bâtiment !")
            
        # Vérifie si le quartier général de niveau 1 existe avant de construire d'autres bâtiments
        if building_name != "quartier_general" and current_level == 0 and faction_buildings.get("quartier_general", 0) == 0:
            raise ValueError("Vous devez d'abord construire un Quartier Général de niveau 1 !")
            
        # Obtient le coût du bâtiment
        costs = buildings[building_name]["niveaux"][current_level + 1]["cout"]
        
        # Vérifie si la faction a assez de ressources
        faction_resources = factions[user_faction]["resources"]
        for resource, amount in costs.items():
            if faction_resources.get(resource, 0) < amount:
                raise ValueError(f"Ressources insuffisantes ! Il vous manque {amount - faction_resources.get(resource, 0)} {resource}.")
        
        # Déduit les ressources
        for resource, amount in costs.items():
            faction_resources[resource] -= amount
        
        # Construit ou améliore le bâtiment
        faction_buildings[building_name] = current_level + 1
        factions[user_faction]["buildings"] = faction_buildings
        
        self._save_factions(factions)
        
        building_info = buildings[building_name]
        level_info = building_info["niveaux"][current_level + 1]
        
        return f"Bâtiment '{building_info['nom']}' construit au niveau {current_level + 1} ! Bonus: {level_info['bonus']}"
    
    async def transfer_resource(self, interaction: discord.Interaction, target_faction: str, resource: str, amount: int):
        """Transfère des ressources à une autre faction"""
        # Vérifie que la ressource existe
        valid_resources = ["bois", "pierre", "fer", "or"]
        if resource not in valid_resources:
            raise ValueError(f"Ressource invalide ! Les ressources disponibles sont: {', '.join(valid_resources)}")
            
        factions = self._load_factions()
        
        # Trouve la faction de l'utilisateur
        source_faction = None
        for faction_name, faction_data in factions.items():
            role = interaction.guild.get_role(faction_data["role_id"])
            if role and role in interaction.user.roles:
                source_faction = faction_name
                break
                
        if not source_faction:
            raise ValueError("Vous n'êtes pas membre d'une faction !")
            
        if target_faction not in factions:
            raise ValueError(f"La faction cible '{target_faction}' n'existe pas !")
            
        if source_faction == target_faction:
            raise ValueError("Vous ne pouvez pas transférer vers votre propre faction !")
            
        # Vérifie que l'utilisateur a assez de ressources
        source_resources = factions[source_faction]["resources"]
        if source_resources.get(resource, 0) < amount:
            raise ValueError(f"Ressources insuffisantes ! Vous avez {source_resources.get(resource, 0)} {resource}")
            
        # Effectue le transfert
        source_resources[resource] -= amount
        factions[target_faction]["resources"][resource] += amount
        
        self._save_factions(factions)
        
        return f"Transfert réussi ! Vous avez envoyé {amount} {resource} à '{target_faction}'."
