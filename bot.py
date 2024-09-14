import os
import pandas as pd
import vobject
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Ganti dengan token API dari BotFather
TOKEN = '7448625615:AAEhubh7IVGNia98WkXxCZCvpI2Z3vnEsHk'

# State untuk percakapan
ASK_BASE_NAME, ASK_FILENAME = range(2)

# Tempat menyimpan data sementara
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Halo! Kirimkan file CSV, TXT, atau Excel (XLS/XLSX) yang berisi nomor telepon.")

def convert_to_vcf(phone_numbers, base_name, output_vcf):
    with open(output_vcf, 'w') as vcf:
        for i, phone in enumerate(phone_numbers, start=1):
            vcard = vobject.vCard()
            vcard.add('fn').value = f"{base_name} {i}"
            vcard.add('tel').value = phone
            vcf.write(vcard.serialize())

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    file = await context.bot.get_file(update.message.document.file_id)
    file_name = file.file_path.split("/")[-1]
    
    await file.download_to_drive(file_name)
    
    try:
        if file_name.endswith('.csv'):
            data = pd.read_csv(file_name, header=None)
            phone_numbers = data[0].tolist()
        elif file_name.endswith('.txt'):
            with open(file_name, 'r') as f:
                phone_numbers = [line.strip() for line in f.readlines() if line.strip()]
        elif file_name.endswith('.xls') or file_name.endswith('.xlsx'):
            data = pd.read_excel(file_name, header=None)
            phone_numbers = data[0].tolist()
        else:
            await update.message.reply_text("Format file tidak didukung.")
            return ConversationHandler.END
        
        user_data[update.message.chat.id] = phone_numbers
        await update.message.reply_text("Masukkan nama dasar yang ingin digunakan untuk kontak:")
    finally:
        if os.path.exists(file_name):
            os.remove(file_name)

    return ASK_BASE_NAME

async def ask_base_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    base_name = update.message.text
    user_data[update.message.chat.id + "_base_name"] = base_name
    await update.message.reply_text("Sekarang, masukkan nama file VCF yang diinginkan (tanpa ekstensi):")
    return ASK_FILENAME

async def ask_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    vcf_filename = update.message.text + ".vcf"
    phone_numbers = user_data.get(update.message.chat.id)
    base_name = user_data.get(update.message.chat.id + "_base_name")
    
    if not phone_numbers or not base_name:
        await update.message.reply_text("Terjadi kesalahan dalam data yang diterima.")
        return ConversationHandler.END
    
    convert_to_vcf(phone_numbers, base_name, vcf_filename)
    
    with open(vcf_filename, 'rb') as vcf_file:
        await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(vcf_file, filename=vcf_filename))
    
    if os.path.exists(vcf_filename):
        os.remove(vcf_filename)
    
    user_data.pop(update.message.chat.id, None)
    user_data.pop(update.message.chat.id + "_base_name", None)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

async def main():
    application = Application.builder().token(TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Document.ALL, handle_document)],
        states={
            ASK_BASE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_base_name)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("start", start))

    await application.initialize()
    await application.start()
    await application.updater.start_polling()

if __name__ == '__main__':
    import asyncio
    asyncio.run(main())
