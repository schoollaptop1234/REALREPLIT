# ✅ COMPLETED: Successfully added pagination to bot.py
# 
# New commands added:
# - !newshop - Browse the shop with Previous/Next page buttons
# - !newcollection - View collection with pagination and Full Stats button

class CollectionPaginationView(View):
    def __init__(self, user_id: int, user_collection: list, target_user_id: int = None, items_per_page: int = 8):
        super().__init__(timeout=120)
        self.user_id = user_id
        self.user_collection = user_collection
        self.target_user_id = target_user_id or user_id
        self.items_per_page = items_per_page
        self.current_page = 0
        self.max_pages = max(0, (len(user_collection) - 1) // items_per_page)
        
        # Update button states
        self.update_buttons()
    
    def update_buttons(self):
        # Enable/disable buttons based on current page
        self.children[0].disabled = self.current_page <= 0  # Previous button
        self.children[1].disabled = self.current_page >= self.max_pages  # Next button
        
        # Update labels with page info
        self.children[0].label = f"⬅️ Previous"
        self.children[1].label = f"Next ➡️"
    
    def get_current_page_items(self):
        start_idx = self.current_page * self.items_per_page
        end_idx = start_idx + self.items_per_page
        return self.user_collection[start_idx:end_idx]
    
    def create_collection_embed(self):
        current_items = self.get_current_page_items()
        
        if self.user_id == self.target_user_id:
            title = "⚽ **Your Football Card Collection** ⚽"
            max_storage = get_user_max_storage(self.user_id)
            description = f"📦 **{len(self.user_collection)}/{max_storage} cards** | Page {self.current_page + 1}/{self.max_pages + 1}"
        else:
            target_user = bot.get_user(self.target_user_id)
            username = target_user.display_name if target_user else "User"
            title = f"⚽ **{username}'s Collection** ⚽"
            description = f"📦 **{len(self.user_collection)} cards** | Page {self.current_page + 1}/{self.max_pages + 1}"
        
        embed = discord.Embed(
            title=title,
            description=description,
            color=0x3498db
        )
        
        if not current_items:
            embed.add_field(
                name="📭 Empty Collection",
                value="No cards on this page. Use `!buy <player>` to get cards!",
                inline=False
            )
            return embed
        
        # Calculate total value for current page
        page_value = sum(card.get("price", 0) for card in current_items)
        
        # Add cards to embed
        for i, card in enumerate(current_items, start=(self.current_page * self.items_per_page + 1)):
            upgrade_level = get_card_upgrade_level(card)
            upgrade_progress = card.get("upgrade_progress", 0)
            
            # Build card info - CORRECTED SYNTAX
            card_info = f"🏆 **{card['rarity']}** | 💰 ${card['price']:,}\n"
            card_info += f"⭐ Level: **{upgrade_level}**"
            
            if upgrade_level != "Ultimate" and upgrade_progress > 0:
                card_info += f" ({upgrade_progress}% progress)"
            
            embed.add_field(
                name=f"{i}. {card['name']}",
                value=card_info,
                inline=True
            )
        
        # Add page summary
        embed.add_field(
            name="📊 **Page Summary**",
            value=f"💰 Page Value: ${page_value:,}\n📦 Cards shown: {len(current_items)}",
            inline=False
        )
        
        if self.user_id == self.target_user_id:
            embed.set_footer(text="💡 Use !sell <number> to sell cards | !upgrade <number> to upgrade")
        
        return embed
    
    @discord.ui.button(label="⬅️ Previous", style=discord.ButtonStyle.secondary)
    async def previous_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your collection view!", ephemeral=True)
            return
        
        if self.current_page > 0:
            self.current_page -= 1
            self.update_buttons()
            embed = self.create_collection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on first page!", ephemeral=True)
    
    @discord.ui.button(label="Next ➡️", style=discord.ButtonStyle.secondary)
    async def next_page(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your collection view!", ephemeral=True)
            return
        
        if self.current_page < self.max_pages:
            self.current_page += 1
            self.update_buttons()
            embed = self.create_collection_embed()
            await interaction.response.edit_message(embed=embed, view=self)
        else:
            await interaction.response.send_message("❌ Already on last page!", ephemeral=True)
    
    @discord.ui.button(label="📊 Full Stats", style=discord.ButtonStyle.primary)
    async def show_full_stats(self, interaction: discord.Interaction, button: Button):
        if interaction.user.id != self.user_id:
            await interaction.response.send_message("❌ This is not your collection view!", ephemeral=True)
            return
        
        # Calculate collection statistics
        total_value = sum(card.get("price", 0) for card in self.user_collection)
        total_income = sum(card.get("income_rate", 0) for card in self.user_collection)
        
        # Count by rarity
        rarity_counts = {}
        for card in self.user_collection:
            rarity = card.get("rarity", "Common")
            rarity_counts[rarity] = rarity_counts.get(rarity, 0) + 1
        
        # Count by upgrade level
        upgrade_counts = {}
        for card in self.user_collection:
            level = get_card_upgrade_level(card)
            upgrade_counts[level] = upgrade_counts.get(level, 0) + 1
        
        if self.user_id == self.target_user_id:
            title = "📊 **Your Collection Statistics** 📊"
        else:
            target_user = bot.get_user(self.target_user_id)
            username = target_user.display_name if target_user else "User"
            title = f"📊 **{username}'s Collection Statistics** 📊"
        
        embed = discord.Embed(title=title, color=0x00ff00)
        
        embed.add_field(
            name="💰 **Financial Summary**",
            value=f"Total Value: ${total_value:,}\nPassive Income: ${total_income:,}/hour",
            inline=True
        )
        
        embed.add_field(
            name="📦 **Collection Size**",
            value=f"Total Cards: {len(self.user_collection)}",
            inline=True
        )
        
        if rarity_counts:
            rarity_text = "\n".join([f"{rarity}: {count}" for rarity, count in sorted(rarity_counts.items())])
            embed.add_field(
                name="🏆 **By Rarity**",
                value=rarity_text,
                inline=True
            )
        
        if upgrade_counts:
            upgrade_text = "\n".join([f"{level}: {count}" for level, count in sorted(upgrade_counts.items())])
            embed.add_field(
                name="⭐ **By Upgrade Level**",
                value=upgrade_text,
                inline=True
            )
        
        await interaction.response.edit_message(embed=embed, view=self)