import os
import logging
import io
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext, CallbackQueryHandler
from PIL import Image

# ============================
# CONFIGURATION
# ============================

# Get bot token from environment variable (set this in Railway)
BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not BOT_TOKEN:
    logging.error("❌ TELEGRAM_BOT_TOKEN environment variable not set!")
    exit(1)

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Supported formats with descriptions and file extensions
SUPPORTED_FORMATS = {
    'PNG': {'desc': 'Portable Network Graphics (Lossless)', 'ext': 'png'},
    'JPEG': {'desc': 'Joint Photographic Experts Group (Lossy)', 'ext': 'jpg'},
    'WEBP': {'desc': 'Google WebP Format', 'ext': 'webp'},
    'BMP': {'desc': 'Bitmap Image', 'ext': 'bmp'},
    'GIF': {'desc': 'Graphics Interchange Format', 'ext': 'gif'},
    'TIFF': {'desc': 'Tagged Image File Format', 'ext': 'tiff'},
}

# ============================
# HELPER FUNCTIONS
# ============================

async def convert_image(input_bytes: bytes, target_format: str):
    """
    Convert an image to the target format.
    Returns the converted image as bytes and original format.
    """
    try:
        # Open the image from bytes
        img = Image.open(io.BytesIO(input_bytes))
        
        # Get original format
        original_format = img.format if img.format else "Unknown"
        
        # Convert RGBA to RGB for JPEG (which doesn't support transparency)
        if target_format.upper() == 'JPEG' and img.mode in ('RGBA', 'P'):
            img = img.convert('RGB')
        
        # Save to bytes
        output_buffer = io.BytesIO()
        img.save(output_buffer, format=target_format.upper())
        output_buffer.seek(0)
        
        return output_buffer.read(), original_format
        
    except Exception as e:
        logger.error(f"Conversion error: {e}")
        raise e

def is_image_file(filename: str) -> bool:
    """Check if a filename has an image extension."""
    image_extensions = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tiff', '.tif'}
    return any(filename.lower().endswith(ext) for ext in image_extensions)

# ============================
# BOT COMMAND HANDLERS
# ============================

async def start(update: Update, context: CallbackContext) -> None:
    """Handle /start command."""
    user = update.effective_user
    welcome_msg = (
        f"👋 Hello {user.first_name}!\n\n"
        "Welcome to **PixxConvert Bot** 🖼️\n"
        "I convert images to different formats instantly!\n\n"
        "**📌 How to use:**\n"
        "1. Send me any image (photo or file).\n"
        "2. Click the **'🔄 Convert'** button.\n"
        "3. Choose your desired format.\n"
        "4. Receive your converted image!\n\n"
        "**📋 Commands:**\n"
        "/start - Show this message\n"
        "/help - Get help\n"
        "/formats - List all supported formats\n"
        "/about - About this bot\n\n"
        "💡 Tip: You can send multiple images one by one!"
    )
    await update.message.reply_text(welcome_msg)

async def help_command(update: Update, context: CallbackContext) -> None:
    """Handle /help command."""
    help_msg = (
        "**🤖 PixxConvert Bot Help**\n\n"
        "**How to convert an image:**\n"
        "1. Send me an image (as a photo or file).\n"
        "2. I'll show a 'Convert' button.\n"
        "3. Click it and select your format.\n"
        "4. I'll send the converted image back.\n\n"
        "**Supported Formats:**\n"
        "PNG, JPEG, WEBP, BMP, GIF, TIFF\n\n"
        "**Commands:**\n"
        "/start - Start the bot\n"
        "/help - Show this help\n"
        "/formats - List all formats\n"
        "/about - About this bot\n\n"
        "**⚠️ Note:** Large images may take a moment to process."
    )
    await update.message.reply_text(help_msg)

async def formats_command(update: Update, context: CallbackContext) -> None:
    """Handle /formats command."""
    fmt_list = []
    for fmt, data in SUPPORTED_FORMATS.items():
        fmt_list.append(f"• **{fmt}** - {data['desc']}")
    
    msg = "**📋 Supported Image Formats:**\n\n" + "\n".join(fmt_list)
    await update.message.reply_text(msg)

async def about_command(update: Update, context: CallbackContext) -> None:
    """Handle /about command."""
    about_msg = (
        "**ℹ️ About PixxConvert Bot**\n\n"
        "Version: 1.0.0\n"
        "Created with: python-telegram-bot & Pillow\n"
        "Hosted on: Railway\n\n"
        "**Features:**\n"
        "✅ Convert between multiple image formats\n"
        "✅ Support for photos and document images\n"
        "✅ Easy-to-use inline buttons\n"
        "✅ Fast and reliable\n\n"
        "Made with ❤️ for the Telegram community"
    )
    await update.message.reply_text(about_msg)

# ============================
# IMAGE HANDLER
# ============================

async def handle_image(update: Update, context: CallbackContext) -> None:
    """Handle incoming images and show conversion options."""
    try:
        # Check if it's a photo or a document
        if update.message.photo:
            # Get the largest photo
            photo_file = await update.message.photo[-1].get_file()
            file_bytes = await photo_file.download_as_bytearray()
            file_name = f"image_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            
        elif update.message.document:
            # Check if it's an image file
            doc = update.message.document
            if not is_image_file(doc.file_name or ''):
                await update.message.reply_text(
                    "❌ Please send an image file (JPG, PNG, GIF, BMP, WEBP, TIFF)."
                )
                return
            
            file = await doc.get_file()
            file_bytes = await file.download_as_bytearray()
            file_name = doc.file_name or "image"
        
        else:
            await update.message.reply_text("❌ Please send me an image!")
            return
        
        # Store the image in context for later use
        context.user_data['image_bytes'] = file_bytes
        context.user_data['file_name'] = file_name
        
        # Create inline keyboard
        keyboard = [
            [InlineKeyboardButton("🔄 Convert This Image", callback_data='show_formats')],
            [InlineKeyboardButton("❌ Cancel", callback_data='cancel')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            f"✅ Image received: **{file_name}**\n\n"
            "Click the button below to convert it!",
            reply_markup=reply_markup
        )
        
    except Exception as e:
        logger.error(f"Error handling image: {e}")
        await update.message.reply_text(
            "❌ Sorry, I couldn't process your image. Please try again."
        )

# ============================
# BUTTON CALLBACK HANDLER
# ============================

async def button_callback(update: Update, context: CallbackContext) -> None:
    """Handle all button callbacks."""
    query = update.callback_query
    await query.answer()
    
    # Check if we have an image stored
    if 'image_bytes' not in context.user_data:
        await query.edit_message_text(
            "❌ No image found! Please send me an image first."
        )
        return
    
    if query.data == 'show_formats':
        # Create format selection buttons
        keyboard = []
        row = []
        for idx, fmt in enumerate(SUPPORTED_FORMATS.keys()):
            row.append(InlineKeyboardButton(fmt, callback_data=f'convert_{fmt}'))
            if len(row) == 2:  # 2 buttons per row
                keyboard.append(row)
                row = []
        if row:  # Add remaining button
            keyboard.append(row)
        
        # Add cancel button
        keyboard.append([InlineKeyboardButton("❌ Cancel", callback_data='cancel')])
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            "**🎨 Choose the output format:**",
            reply_markup=reply_markup
        )
    
    elif query.data.startswith('convert_'):
        target_format = query.data.replace('convert_', '')
        await handle_conversion(update, context, target_format)
    
    elif query.data == 'cancel':
        # Clear stored image
        context.user_data.pop('image_bytes', None)
        context.user_data.pop('file_name', None)
        await query.edit_message_text("✅ Conversion cancelled. Send me another image to convert!")

# ============================
# CONVERSION HANDLER
# ============================

async def handle_conversion(update: Update, context: CallbackContext, target_format: str) -> None:
    """Perform the actual image conversion."""
    query = update.callback_query
    user_id = query.from_user.id
    
    try:
        # Get stored image
        image_bytes = context.user_data.get('image_bytes')
        original_name = context.user_data.get('file_name', 'image')
        
        if not image_bytes:
            await query.edit_message_text("❌ No image found. Please send me an image first!")
            return
        
        # Show processing message
        await query.edit_message_text(f"🔄 Converting to **{target_format}**... Please wait.")
        
        # Perform conversion
        converted_bytes, original_format = await convert_image(image_bytes, target_format)
        
        # Prepare new filename
        base_name = os.path.splitext(original_name)[0]
        new_filename = f"{base_name}.{SUPPORTED_FORMATS[target_format]['ext']}"
        
        # Send the converted image
        await query.edit_message_text(
            f"✅ **Conversion Complete!**\n\n"
            f"📄 Original: {original_format or 'Unknown'}\n"
            f"🎯 Target: {target_format}\n"
            f"📁 File: {new_filename}"
        )
        
        # Send the converted file
        await context.bot.send_document(
            chat_id=user_id,
            document=io.BytesIO(converted_bytes),
            filename=new_filename,
            caption="🎉 Your converted image is ready!"
        )
        
        # Clear the stored image after conversion
        context.user_data.pop('image_bytes', None)
        context.user_data.pop('file_name', None)
        
    except Exception as e:
        logger.error(f"Conversion error for user {user_id}: {e}")
        await query.edit_message_text(
            f"❌ Sorry, an error occurred while converting.\n\n"
            f"Error: {str(e)[:100]}\n\n"
            "Please try again with a different image or format."
        )

# ============================
# ERROR HANDLER
# ============================

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Log and handle errors."""
    logger.error(f"Update {update} caused error {context.error}")
    try:
        if update and update.effective_message:
            await update.effective_message.reply_text(
                "⚠️ Something went wrong. Please try again later."
            )
    except:
        pass

# ============================
# MAIN
# ============================

def main() -> None:
    """Start the bot."""
    logger.info("🚀 Starting PixxConvert Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("formats", formats_command))
    application.add_handler(CommandHandler("about", about_command))
    
    # Register message handlers
    application.add_handler(MessageHandler(filters.PHOTO | filters.Document.IMAGE, handle_image))
    
    # Register callback handler
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("✅ Bot is running!")
    application.run_polling()

if __name__ == '__main__':
    main()
