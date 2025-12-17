const { TelegramClient } = require('telegram');
const { StringSession } = require('telegram/sessions');
const { NewMessage } = require('telegram/events');
const dotenv = require('dotenv');
const fs = require('fs');
const path = require('path');


// Add this at the TOP of copier.js
const http = require('http');

// Start health check server
const healthServer = http.createServer((req, res) => {
  if (req.url === '/health') {
    res.writeHead(200, { 'Content-Type': 'application/json' });
    res.end(JSON.stringify({ 
      status: 'UP', 
      service: 'telegram-forwarder',
      timestamp: new Date().toISOString(),
      uptime: process.uptime()
    }));
  } else {
    res.writeHead(404);
    res.end('Not found');
  }
});

healthServer.listen(3000, '0.0.0.0', () => {
  console.log('✅ Health check server running on port 3000');
});

// Load environment variables
dotenv.config();

// Configuration
const getConfig = () => {
  const config = {
    apiId: parseInt(process.env.API_ID),
    apiHash: process.env.API_HASH,
    sessionString: process.env.SESSION_STRING || "",
    sourceChannels: process.env.SOURCE_CHANNELS ? process.env.SOURCE_CHANNELS.split(',').map(ch => ch.trim()) : ['@myachPRO'],
    targetChannel: process.env.TARGET_CHANNEL || '@livefootball671',
    keywords: process.env.KEYWORDS ? process.env.KEYWORDS.split(',').map(k => k.trim().toLowerCase()) : [],
    blockedWords: process.env.BLOCKED_WORDS ? process.env.BLOCKED_WORDS.split(',').map(b => b.trim().toLowerCase()) : [],
    removeSource: process.env.REMOVE_SOURCE !== 'false',
    enableTranslation: process.env.ENABLE_TRANSLATION !== 'false'
  };

  // Validate required configuration
  console.log('🔍 Checking configuration...');
  console.log('API_ID:', config.apiId);
  console.log('API_HASH:', config.apiHash ? '✓ Set' : '✗ Missing');
  console.log('SESSION_STRING:', config.sessionString ? '✓ Set' : '✗ Missing');
  console.log('SOURCE_CHANNELS:', config.sourceChannels);
  console.log('TARGET_CHANNEL:', config.targetChannel);
  console.log('TRANSLATION:', config.enableTranslation ? '✓ Enabled' : '✗ Disabled');

  if (!config.apiId || !config.apiHash) {
    throw new Error('API_ID or API_HASH is missing from .env file');
  }

  if (!config.sessionString) {
    throw new Error('SESSION_STRING is missing from .env file');
  }

  return config;
};

const config = getConfig();

// Create downloads directory
const downloadsDir = './downloads';
if (!fs.existsSync(downloadsDir)) {
  fs.mkdirSync(downloadsDir, { recursive: true });
}

// Free translation using Google Translate
async function translateToEnglish(text) {
    if (!text || text.trim().length === 0) return '';
    
    try {
        console.log('🌐 Translating text...');
        
        const translate = require('@iamtraction/google-translate');
        
        const result = await translate(text, { from: 'ru', to: 'en' });
        
        console.log('✅ Translation successful');
        console.log(`📝 Original: ${text.substring(0, 80)}...`);
        console.log(`🔤 Translated: ${result.text.substring(0, 80)}...`);
        
        return result.text;
        
    } catch (error) {
        console.log('❌ Translation failed, using fallback:', error.message);
        return simpleTranslate(text); // Use simple fallback
    }
}

// Simple word-based translation fallback
function simpleTranslate(text) {
    if (!text) return '';
    
    const commonTranslations = {
        // Football terms
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
        
        // Common words
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
    };
    
    let translated = text;
    Object.keys(commonTranslations).forEach(russian => {
        const regex = new RegExp(russian, 'g');
        translated = translated.replace(regex, commonTranslations[russian]);
    });
    
    // Add translation indicator if any changes were made
    if (translated !== text) {
        return translated + ' [Auto-Translated]';
    }
    
    return text;
}

function cleanMessageText(text) {
    if (!text) return '';
    
    // Remove @myachPRO mentions (case insensitive)
    let cleanText = text.replace(/@myachPRO/gi, '');
    
    // Also remove any standalone "myachPRO" without @
    cleanText = cleanText.replace(/\bmyachPRO\b/gi, '');
    
    // Remove Fabrizio mentions and links
    cleanText = cleanText.replace(/@FabrizioRomanoTG/gi, '');
    cleanText = cleanText.replace(/@FabrizioRomano/gi, '');
    cleanText = cleanText.replace(/Fabrizio/gi, '');
    cleanText = cleanText.replace(/Romano/gi, '');
    cleanText = cleanText.replace(/https:\/\/t\.me\/FabrizioRomano/gi, '');
    cleanText = cleanText.replace(/t\.me\/FabrizioRomano/gi, '');
    
    // Clean up extra spaces and newlines that might result from removal
    cleanText = cleanText.replace(/\n\s*\n/g, '\n'); // Remove empty lines
    cleanText = cleanText.trim();
    
    return cleanText;
}

// Function to truncate caption if too long for Telegram
function truncateCaption(caption, maxLength = 1024) {
    if (!caption || caption.length <= maxLength) return caption;
    
    console.log(`📏 Truncating caption from ${caption.length} to ${maxLength} characters`);
    return caption.substring(0, maxLength - 3) + '...';
}

class MessageCopier {
    constructor(client) {
        this.client = client;
        this.processedMessages = new Set();
        this.channelEntities = new Map();
    }

    async initialize() {
        console.log('\n🔄 Initializing channel access...');
        console.log('──────────────────────────────────');
        
        for (const channel of config.sourceChannels) {
            try {
                console.log(`🔍 Testing access to: ${channel}`);
                const entity = await this.client.getEntity(channel);
                this.channelEntities.set(channel, entity);
                console.log(`✅ Successfully accessed: ${entity.title}`);
                
                // Try to get the last message to verify we can read messages
                const messages = await this.client.getMessages(entity, { limit: 1 });
                if (messages.length > 0) {
                    console.log(`📨 Last message preview: ${messages[0].text ? messages[0].text.substring(0, 50) + '...' : '[Media Message]'}`);
                } else {
                    console.log('ℹ️ No recent messages found in this channel');
                }
                
            } catch (error) {
                console.log(`❌ Cannot access ${channel}: ${error.message}`);
                return false;
            }
            console.log('');
        }
        return true;
    }

    async copyTodayMessages() {
        console.log('\n📅 COPYING TODAY\'S MESSAGES...');
        console.log('──────────────────────────────────');

        const today = new Date();
        today.setHours(0, 0, 0, 0);
        let totalCopied = 0;

        for (const channel of config.sourceChannels) {
            try {
                const entity = this.channelEntities.get(channel);
                console.log(`🔍 Scanning today's messages from: ${entity.title}`);
                
                const messages = await this.client.getMessages(entity, { limit: 50 });
                
                const todayMessages = messages.filter(msg => {
                    const messageDate = new Date(msg.date * 1000);
                    return messageDate >= today;
                });

                console.log(`📊 Found ${todayMessages.length} messages from today`);

                for (const message of todayMessages.reverse()) {
                    const messageId = `${message.chatId}-${message.id}`;
                    
                    if (this.processedMessages.has(messageId)) {
                        continue;
                    }

                    const messageText = message.text || message.message || "";
                    console.log(`\n📩 Processing message from today:`);
                    console.log(`📝 Content: ${messageText.substring(0, 80)}...`);

                    if (!await this.shouldCopy(message)) {
                        continue;
                    }

                    if (message.media) {
                        await this.copyMedia(message, entity.title);
                    } else if (messageText) {
                        await this.copyText(message, entity.title);
                    }

                    this.processedMessages.add(messageId);
                    totalCopied++;

                    await new Promise(resolve => setTimeout(resolve, 2000));
                }

            } catch (error) {
                console.log(`❌ Error scanning ${channel}:`, error.message);
            }
        }

        console.log('\n──────────────────────────────────');
        console.log(`✅ COMPLETED: Copied ${totalCopied} messages from today`);
        console.log('👀 Now switching to real-time monitoring...');
        console.log('──────────────────────────────────\n');
        
        return totalCopied;
    }

    async setupMonitoring() {
        console.log('🎯 Setting up real-time monitoring...');
        
        for (const channel of config.sourceChannels) {
            try {
                this.client.addEventHandler(this.processMessage.bind(this), new NewMessage({
                    chats: [channel]
                }));
                console.log(`✅ Now listening to: ${channel}`);
            } catch (error) {
                console.log(`❌ Failed to listen to ${channel}: ${error.message}`);
            }
        }
    }

    async processMessage(event) {
        try {
            const message = event.message;
            
            let chatTitle = 'Unknown Channel';
            try {
                const chat = await message.getChat();
                chatTitle = chat.title || 'Unknown Channel';
            } catch (e) {
                console.log('⚠️ Could not get chat title');
            }
            
            const messageText = message.text || message.message || "";
            const messageId = `${message.chatId}-${message.id}`;
            
            console.log('\n🎯 NEW MESSAGE DETECTED!');
            console.log(`📡 From: ${chatTitle}`);
            console.log(`📝 Content: ${messageText.substring(0, 100)}${messageText.length > 100 ? '...' : ''}`);
            console.log(`🆔 Message ID: ${message.id}`);
            console.log(`⏰ Time: ${new Date().toLocaleTimeString()}`);

            if (this.processedMessages.has(messageId)) {
                console.log('⏭️ Already processed, skipping...');
                return;
            }
            this.processedMessages.add(messageId);

            if (!await this.shouldCopy(message)) {
                return;
            }

            console.log('✅ Filters passed, copying message...');

            await new Promise(resolve => setTimeout(resolve, 1000));

            if (message.media) {
                await this.copyMedia(message, chatTitle);
            } else if (messageText) {
                await this.copyText(message, chatTitle);
            }

            console.log(`✅ SUCCESS: Message copied to ${config.targetChannel}`);

        } catch (error) {
            console.error('❌ Error processing message:', error.message);
        }
    }

    async shouldCopy(message) {
        const text = message.text || message.message || "";
        const textLower = text.toLowerCase();

        if (config.blockedWords.some(word => textLower.includes(word))) {
            console.log('🚫 Blocked: Contains blocked words');
            return false;
        }

        if (config.keywords.length > 0) {
            const hasKeyword = config.keywords.some(keyword => textLower.includes(keyword));
            if (!hasKeyword) {
                console.log('⏭️ Skipped: No keywords match');
                return false;
            }
        }

        console.log('✅ All filters passed');
        return true;
    }

    async copyMedia(message, chatTitle) {
        try {
            const isPhoto = message.photo;
            const mediaType = isPhoto ? 'photo' : 'video';
            console.log(`📥 Processing ${mediaType}...`);
            
            const originalCaption = message.text || message.message || "";
            let cleanCaption = cleanMessageText(originalCaption);
            
            if (cleanCaption && config.enableTranslation) {
                cleanCaption = await translateToEnglish(cleanCaption);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            
            if (config.removeSource) {
                cleanCaption = cleanCaption
                    .replace(/🔗\s*Source:.*/gi, '')
                    .replace(/📌\s*From:.*/gi, '')
                    .trim();
            } else {
                if (cleanCaption) {
                    cleanCaption += `\n\n🔗 Source: ${chatTitle}`;
                } else {
                    cleanCaption = `🔗 Source: ${chatTitle}`;
                }
            }

            cleanCaption = truncateCaption(cleanCaption || `🏆 Football ${mediaType === 'photo' ? 'Photo' : 'Video'}`);

            // Use sendFile instead of sendMedia
            await this.client.sendFile(config.targetChannel, {
                file: message.media,
                caption: cleanCaption
            });
            
            console.log(`✅ ${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} sent successfully!`);

        } catch (error) {
            console.log('❌ Primary method failed:', error.message);
            await this.fallbackMediaSend(message, chatTitle);
        }
    }

    async fallbackMediaSend(message, chatTitle) {
        console.log('🔄 Trying fallback method...');
        
        try {
            const isPhoto = message.photo;
            const mediaType = isPhoto ? 'photo' : 'video';
            
            const mediaBuffer = await this.client.downloadMedia(message);
            
            const extension = isPhoto ? '.jpg' : '.mp4';
            const tempFile = path.join(__dirname, `temp_${mediaType}_${Date.now()}${extension}`);
            fs.writeFileSync(tempFile, mediaBuffer);
            
            const originalCaption = message.text || message.message || "";
            let cleanCaption = cleanMessageText(originalCaption);
            
            if (cleanCaption && config.enableTranslation) {
                cleanCaption = await translateToEnglish(cleanCaption);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }
            
            if (config.removeSource) {
                cleanCaption = cleanCaption
                    .replace(/🔗\s*Source:.*/gi, '')
                    .replace(/📌\s*From:.*/gi, '')
                    .trim();
            } else {
                if (cleanCaption) {
                    cleanCaption += `\n\n🔗 Source: ${chatTitle}`;
                } else {
                    cleanCaption = `🔗 Source: ${chatTitle}`;
                }
            }

            cleanCaption = truncateCaption(cleanCaption || `🏆 Football ${mediaType === 'photo' ? 'Photo' : 'Video'}`);

            await this.client.sendFile(config.targetChannel, {
                file: tempFile,
                caption: cleanCaption
            });
            
            console.log(`✅ ${mediaType.charAt(0).toUpperCase() + mediaType.slice(1)} sent via fallback method!`);
            
            fs.unlinkSync(tempFile);
            
        } catch (error) {
            console.log(`❌ Fallback also failed:`, error.message);
        }
    }

    async copyText(message, chatTitle) {
        try {
            let cleanText = message.text || message.message || "";

            cleanText = cleanMessageText(cleanText);

            if (cleanText && config.enableTranslation) {
                cleanText = await translateToEnglish(cleanText);
                await new Promise(resolve => setTimeout(resolve, 1000));
            }

            if (config.removeSource) {
                cleanText = cleanText
                    .replace(/🔗\s*Source:.*/gi, '')
                    .replace(/📌\s*From:.*/gi, '')
                    .replace(/Source:.*/gi, '')
                    .replace(/Via:.*/gi, '')
                    .replace(/@FabrizioRomano/gi, '')
                    .replace(/FabrizioRomano/gi, '')
                    .replace(/Fabrizio/gi, '')
                    .replace(/Romano/gi, '')
                    .replace(/https:\/\/t\.me\/FabrizioRomano/gi, '')
                    .replace(/t\.me\/FabrizioRomano/gi, '')
                    .trim();
            } else {
                cleanText += `\n\n🔗 Source: ${chatTitle}`;
            }

            console.log('📤 Sending text to target channel...');
            await this.client.sendMessage(config.targetChannel, {
                message: cleanText
            });
            
            console.log('✅ Text sent successfully');
        } catch (error) {
            console.error('❌ Text copy failed:', error.message);
        }
    }
}

async function main() {
    console.log('🚀 Starting Telegram Message Copier');
    console.log('📝 MODE: COPY & PASTE (not forwarding)');
    if (config.enableTranslation) {
        console.log('🌐 TRANSLATION: Enabled (Russian → English)');
    }
    console.log('──────────────────────────────────');
    
    const session = new StringSession(config.sessionString);
    const client = new TelegramClient(session, config.apiId, config.apiHash, {
        connectionRetries: 5,
    });

    try {
        await client.connect();
        console.log('✅ Connected to Telegram');

        const me = await client.getMe();
        console.log(`👤 Logged in as: ${me.firstName} (@${me.username})`);
        console.log(`📡 Source: ${config.sourceChannels.join(', ')}`);
        console.log(`🎯 Target: ${config.targetChannel}`);
        console.log('──────────────────────────────────');

        const copier = new MessageCopier(client);

        const accessSuccessful = await copier.initialize();
        
        if (!accessSuccessful) {
            console.log('❌ Channel access failed. Please fix the issues above.');
            process.exit(1);
        }

        const copiedCount = await copier.copyTodayMessages();

        await copier.setupMonitoring();

        console.log('\n🟢 BOT IS NOW ACTIVE!');
        console.log('📊 Summary:');
        console.log(`   - Copied ${copiedCount} messages from today`);
        console.log(`   - Now monitoring for NEW messages in real-time`);
        if (config.enableTranslation) {
            console.log(`   - Translation: ENABLED (Russian → English)`);
        }
        console.log('💡 Send a new message to @myachPRO to test');
        console.log('⏹️  Press Ctrl+C to stop the bot');
        console.log('──────────────────────────────────\n');

        await new Promise(() => {});

    } catch (error) {
        console.error('🔴 Fatal error:', error.message);
        process.exit(1);
    }
}

process.on('SIGINT', async () => {
    console.log('\n👋 Shutting down bot gracefully...');
    process.exit(0);
});

main().catch(console.error);
