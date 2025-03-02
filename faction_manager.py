
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
                "role_id": role.id,
                "category_id": category.id,
                "text_channel_id": text_channel.id,
                "voice_channel_id": voice_channel.id
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
