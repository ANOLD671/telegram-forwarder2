import os
import asyncio
import logging
from datetime import datetime, timedelta
from telethon import TelegramClient, events
from telethon.sessions import StringSession
from telethon.tl.types import MessageMediaPhoto, MessageMediaDocument
import re
from googletrans import Translator
from dotenv import load_dotenv
import tempfile

# Load environment variables
load_dotenv()

# Configuration
class Config:
    def __init__(self):
        self.api_id = int(os.getenv('API_ID', 0))
        self.api_hash = os.getenv('API_HASH', '')
        self.session_string = os.getenv('SESSION_STRING', '')
        self.source_channels = [ch.strip() for ch in os.getenv('SOURCE_CHANNELS', '@myachPRO').split(',')]
        self.target_channel = os.getenv('TARGET_CHANNEL', '@livefootball671')
        self.keywords = [k.strip().lower() for k in os.getenv('KEYWORDS', '').split(',')] if os.getenv('KEYWORDS') else []
        self.blocked_words = [b.strip().lower() for b in os.getenv('BLOCKED_WORDS', '').split(',')] if os.getenv('BLOCKED_WORDS') else []
        self.remove_source = os.getenv('REMOVE_SOURCE', 'true').lower() != 'false'
        self.enable_translation = os.getenv('ENABLE_TRANSLATION', 'true').lower() != 'false'
        
        self.validate()
    
    def validate(self):
        print('🔍 Checking configuration...')
        print('API_ID:', self.api_id)
        print('API_HASH:', '✓ Set' if self.api_hash else '✗ Missing')
        print('SESSION_STRING:', '✓ Set' if self.session_string else '✗ Missing')
        print('SOURCE_CHANNELS:', self.source_channels)
        print('TARGET_CHANNEL:', self.target_channel)
        print('KEYWORDS:', self.keywords if self.keywords else 'None (all messages will be copied)')
        print('BLOCKED_WORDS:', self.blocked_words)
        print('REMOVE_SOURCE:', self.remove_source)
        print('TRANSLATION:', '✓ Enabled' if self.enable_translation else '✗ Disabled')
        
        if not self.api_id or not self.api_hash:
            raise ValueError('API_ID or API_HASH is missing from .env file')
        
        if not self.session_string:
            raise ValueError('SESSION_STRING is missing from .env file')

config = Config()

# Translation setup
translator = Translator()

async def translate_to_english(text):
    if not text or not text.strip():
        return ''
    
    try:
        print('🌐 Translating text...')
        translation = translator.translate(text, src='ru', dest='en')
        print('✅ Translation successful')
        print(f'📝 Original: {text[:80]}...')
        print(f'🔤 Translated: {translation.text[:80]}...')
        return translation.text
    except Exception as error:
        print(f'❌ Translation failed, using fallback: {error}')
        return simple_translate(text)

def simple_translate(text):
    if not text:
        return ''
    
    common_translations = {
        'футбол': 'football', 'Футбол': 'Football',
        'матч': 'match', 'Матч': 'Match',
        'гол': 'goal', 'Гол': 'Goal',
        'команда': 'team', 'Команда': 'Team',
        'игра': 'game', 'Игра': 'Game',
        'лига': 'league', 'Лига': 'League',
        'чемпионат': 'championship', 'Чемпионат': 'Championship',
        'счет': 'score', 'Счет': 'Score',
        'победа': 'victory', 'Победа': 'Victory',
        'поражение': 'defeat', 'Поражение': 'Defeat',
        'ничья': 'draw', 'Ничья': 'Draw',
        'турнир': 'tournament', 'Турнир': 'Tournament',
        'сезон': 'season', 'Сезон': 'Season',
        'болельщик': 'fan', 'Болельщик': 'Fan',
        'тренер': 'coach', 'Тренер': 'Coach',
        'игрок': 'player', 'Игрок': 'Player',
        'вратарь': 'goalkeeper', 'Вратарь': 'Goalkeeper',
        'нападающий': 'forward', 'Нападающий': 'Forward',
        'защитник': 'defender', 'Защитник': 'Defender',
        'сегодня': 'today', 'Сегодня': 'Today',
        'завтра': 'tomorrow', 'Завтра': 'Tomorrow',
        'вчера': 'yesterday', 'Вчера': 'Yesterday',
        'новость': 'news', 'Новость': 'News',
        'новости': 'news', 'Новости': 'News',
        'смотреть': 'watch', 'Смотреть': 'Watch',
        'онлайн': 'online', 'Онлайн': 'Online',
        'прямая': 'live', 'Прямая': 'Live',
        'трансляция': 'broadcast', 'Трансляция': 'Broadcast',
        'результат': 'result', 'Результат': 'Result',
        'обзор': 'review', 'Обзор': 'Review',
        'анонс': 'announcement', 'Анонс': 'Announcement'
    }
    
    translated = text
    for russian, english in common_translations.items():
        translated = translated.replace(russian, english)
    
    if translated != text:
        return translated + ' [Auto-Translated]'
    
    return text

def clean_message_text(text):
    if not text:
        return ''
    
    # Remove @myachPRO mentions
    clean_text = re.sub(r'@myachPRO', '', text, flags=re.IGNORECASE)
    clean_text = re.sub(r'\bmyachPRO\b', '', clean_text, flags=re.IGNORECASE)
    
    # Remove Fabrizio mentions and links
    clean_text = re.sub(r'@FabrizioRomanoTG', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'@FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'Fabrizio', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'Romano', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r'https://t\.me/FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
    clean_text = re.sub(r't\.me/FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
    
    # Clean up extra spaces and newlines
    clean_text = re.sub(r'\n\s*\n', '\n', clean_text)
    clean_text = clean_text.strip()
    
    return clean_text

def truncate_caption(caption, max_length=1024):
    if not caption or len(caption) <= max_length:
        return caption
    
    print(f'📏 Truncating caption from {len(caption)} to {max_length} characters')
    return caption[:max_length - 3] + '...'

class MessageCopier:
    def __init__(self, client):
        self.client = client
        self.processed_messages = set()
        self.channel_entities = {}
    
    async def initialize(self):
        print('\n🔄 Initializing channel access...')
        print('──────────────────────────────────')
        
        for channel in config.source_channels:
            try:
                print(f'🔍 Testing access to: {channel}')
                entity = await self.client.get_entity(channel)
                self.channel_entities[channel] = entity
                print(f'✅ Successfully accessed: {entity.title}')
                
                # Get last message to verify access
                messages = await self.client.get_messages(entity, limit=1)
                if messages:
                    message_text = messages[0].text or messages[0].message or ""
                    preview = message_text[:50] + '...' if message_text else '[Media Message]'
                    print(f'📨 Last message preview: {preview}')
                else:
                    print('ℹ️ No recent messages found in this channel')
                    
            except Exception as error:
                print(f'❌ Cannot access {channel}: {error}')
                return False
            print('')
        return True
    
    async def copy_today_messages(self):
        print('\n📅 COPYING TODAY\'S MESSAGES...')
        print('──────────────────────────────────')

        today = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        total_copied = 0

        for channel in config.source_channels:
            try:
                entity = self.channel_entities[channel]
                print(f'🔍 Scanning today\'s messages from: {entity.title}')
                
                messages = await self.client.get_messages(entity, limit=50)
                
                today_messages = []
                for msg in messages:
                    message_date = msg.date.replace(tzinfo=None)
                    if message_date >= today:
                        today_messages.append(msg)
                
                print(f'📊 Found {len(today_messages)} messages from today')

                for message in reversed(today_messages):
                    message_id = f'{message.chat_id}-{message.id}'
                    
                    if message_id in self.processed_messages:
                        continue
                    
                    message_text = message.text or message.message or ""
                    print(f'\n📩 Processing message from today:')
                    print(f'📝 Content: {message_text[:80]}...')

                    if not await self.should_copy(message):
                        continue

                    if message.media:
                        await self.copy_media(message, entity.title)
                    elif message_text:
                        await self.copy_text(message, entity.title)

                    self.processed_messages.add(message_id)
                    total_copied += 1

                    await asyncio.sleep(2)

            except Exception as error:
                print(f'❌ Error scanning {channel}: {error}')

        print('\n──────────────────────────────────')
        print(f'✅ COMPLETED: Copied {total_copied} messages from today')
        print('👀 Now switching to real-time monitoring...')
        print('──────────────────────────────────\n')
        
        return total_copied
    
    async def setup_monitoring(self):
        print('🎯 Setting up real-time monitoring...')
        
        @self.client.on(events.NewMessage(chats=config.source_channels))
        async def handler(event):
            await self.process_message(event)
        
        for channel in config.source_channels:
            print(f'✅ Now listening to: {channel}')
    
    async def process_message(self, event):
        try:
            message = event.message
            chat = await message.get_chat()
            chat_title = chat.title if hasattr(chat, 'title') else 'Unknown Channel'
            
            message_text = message.text or message.message or ""
            message_id = f'{message.chat_id}-{message.id}'
            
            print('\n🎯 NEW MESSAGE DETECTED!')
            print(f'📡 From: {chat_title}')
            print(f'📝 Content: {message_text[:100]}{"..." if len(message_text) > 100 else ""}')
            print(f'🆔 Message ID: {message.id}')
            print(f'⏰ Time: {datetime.now().strftime("%H:%M:%S")}')

            if message_id in self.processed_messages:
                print('⏭️ Already processed, skipping...')
                return
            
            self.processed_messages.add(message_id)

            if not await self.should_copy(message):
                return

            print('✅ Filters passed, copying message...')

            await asyncio.sleep(1)

            if message.media:
                await self.copy_media(message, chat_title)
            elif message_text:
                await self.copy_text(message, chat_title)

            print(f'✅ SUCCESS: Message copied to {config.target_channel}')

        except Exception as error:
            print(f'❌ Error processing message: {error}')
    
    async def should_copy(self, message):
        text = message.text or message.message or ""
        text_lower = text.lower()

        # Check blocked words
        if any(blocked_word in text_lower for blocked_word in config.blocked_words):
            print('🚫 Blocked: Contains blocked words')
            return False

        # Check keywords (if any are specified)
        if config.keywords:
            if not any(keyword in text_lower for keyword in config.keywords):
                print('⏭️ Skipped: No keywords match')
                return False

        print('✅ All filters passed')
        return True
    
    async def copy_media(self, message, chat_title):
        try:
            is_photo = isinstance(message.media, MessageMediaPhoto)
            media_type = 'photo' if is_photo else 'video'
            print(f'📥 Processing {media_type}...')
            
            original_caption = message.text or message.message or ""
            clean_caption = clean_message_text(original_caption)
            
            if clean_caption and config.enable_translation:
                clean_caption = await translate_to_english(clean_caption)
                await asyncio.sleep(1)
            
            if config.remove_source:
                clean_caption = re.sub(r'🔗\s*Source:.*', '', clean_caption, flags=re.IGNORECASE)
                clean_caption = re.sub(r'📌\s*From:.*', '', clean_caption, flags=re.IGNORECASE)
                clean_caption = clean_caption.strip()
            else:
                if clean_caption:
                    clean_caption += f'\n\n🔗 Source: {chat_title}'
                else:
                    clean_caption = f'🔗 Source: {chat_title}'

            clean_caption = truncate_caption(clean_caption or f'🏆 Football {media_type.capitalize()}')

            # Send media with caption
            await self.client.send_file(
                config.target_channel,
                file=message.media,
                caption=clean_caption
            )
            
            print(f'✅ {media_type.capitalize()} sent successfully!')

        except Exception as error:
            print(f'❌ Primary method failed: {error}')
            await self.fallback_media_send(message, chat_title)
    
    async def fallback_media_send(self, message, chat_title):
        print('🔄 Trying fallback method...')
        
        try:
            is_photo = isinstance(message.media, MessageMediaPhoto)
            media_type = 'photo' if is_photo else 'video'
            
            # Download media
            media_path = await self.client.download_media(message, file=tempfile.NamedTemporaryFile(delete=False).name)
            
            original_caption = message.text or message.message or ""
            clean_caption = clean_message_text(original_caption)
            
            if clean_caption and config.enable_translation:
                clean_caption = await translate_to_english(clean_caption)
                await asyncio.sleep(1)
            
            if config.remove_source:
                clean_caption = re.sub(r'🔗\s*Source:.*', '', clean_caption, flags=re.IGNORECASE)
                clean_caption = re.sub(r'📌\s*From:.*', '', clean_caption, flags=re.IGNORECASE)
                clean_caption = clean_caption.strip()
            else:
                if clean_caption:
                    clean_caption += f'\n\n🔗 Source: {chat_title}'
                else:
                    clean_caption = f'🔗 Source: {chat_title}'

            clean_caption = truncate_caption(clean_caption or f'🏆 Football {media_type.capitalize()}')

            await self.client.send_file(
                config.target_channel,
                file=media_path,
                caption=clean_caption
            )
            
            print(f'✅ {media_type.capitalize()} sent via fallback method!')
            
            # Clean up temp file
            if os.path.exists(media_path):
                os.unlink(media_path)
            
        except Exception as error:
            print(f'❌ Fallback also failed: {error}')
    
    async def copy_text(self, message, chat_title):
        try:
            clean_text = message.text or message.message or ""
            clean_text = clean_message_text(clean_text)

            if clean_text and config.enable_translation:
                clean_text = await translate_to_english(clean_text)
                await asyncio.sleep(1)

            if config.remove_source:
                clean_text = re.sub(r'🔗\s*Source:.*', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'📌\s*From:.*', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'Source:.*', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'Via:.*', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'@FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'Fabrizio', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'Romano', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r'https://t\.me/FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
                clean_text = re.sub(r't\.me/FabrizioRomano', '', clean_text, flags=re.IGNORECASE)
                clean_text = clean_text.strip()
            else:
                clean_text += f'\n\n🔗 Source: {chat_title}'

            print('📤 Sending text to target channel...')
            await self.client.send_message(config.target_channel, clean_text)
            print('✅ Text sent successfully')
            
        except Exception as error:
            print(f'❌ Text copy failed: {error}')

async def main():
    print('🚀 Starting Telegram Message Copier')
    print('📝 MODE: COPY & PASTE (not forwarding)')
    if config.enable_translation:
        print('🌐 TRANSLATION: Enabled (Russian → English)')
    print('──────────────────────────────────')
    
    # Set up logging (reduce telethon noise)
    logging.basicConfig(level=logging.WARNING)
    
    client = TelegramClient(
        StringSession(config.session_string),
        config.api_id,
        config.api_hash
    )

    try:
        await client.start()
        print('✅ Connected to Telegram')

        me = await client.get_me()
        print(f'👤 Logged in as: {me.first_name} (@{me.username})')
        print(f'📡 Source: {", ".join(config.source_channels)}')
        print(f'🎯 Target: {config.target_channel}')
        print('──────────────────────────────────')

        copier = MessageCopier(client)

        access_successful = await copier.initialize()
        
        if not access_successful:
            print('❌ Channel access failed. Please fix the issues above.')
            return

        copied_count = await copier.copy_today_messages()

        await copier.setup_monitoring()

        print('\n🟢 BOT IS NOW ACTIVE!')
        print('📊 Summary:')
        print(f'   - Copied {copied_count} messages from today')
        print(f'   - Now monitoring for NEW messages in real-time')
        if config.enable_translation:
            print(f'   - Translation: ENABLED (Russian → English)')
        print('💡 Send a new message to source channels to test')
        print('⏹️  Press Ctrl+C to stop the bot')
        print('──────────────────────────────────\n')

        # Keep the client running
        await client.run_until_disconnected()

    except Exception as error:
        print(f'🔴 Fatal error: {error}')
    finally:
        await client.disconnect()

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print('\n👋 Shutting down bot gracefully...')