import os
import pandas as pd
import vobject
import asyncio
from telegram import Update, InputFile
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes

# Ganti dengan token API dari BotFather
TOKEN = '7448625615:AAEhubh7IVGNia98WkXxCZCvpI2Z3vnEsHk'

# State untuk percakapan
ASK_BASE_NAME, ASK_FILENAME = range(2)

# Tempat menyimpan data sementara
user_data = {}

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Received /start command")
    await update.message.reply_text("Halo! Kirimkan file CSV, TXT, atau Excel (XLS/XLSX) yang berisi nomor telepon.")

def convert_to_vcf(phone_numbers, base_name, output_vcf):
    print(f"Converting to VCF: {output_vcf}")
    # Mengonversi daftar nomor telepon menjadi file VCF
    with open(output_vcf, 'w') as vcf:
        for i, phone in enumerate(phone_numbers, start=1):
            vcard = vobject.vCard()
            vcard.add('fn').value = f"{base_name} {i}"
            vcard.add('tel').value = phone
            vcf.write(vcard.serialize())
    print(f"VCF file created: {output_vcf}")

async def handle_document(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Handling document")
    # Mendapatkan file yang dikirim pengguna
    file = await context.bot.get_file(update.message.document.file_id)
    file_name = file.file_path.split("/")[-1]
    
    # Download file
    await file.download_to_drive(file_name)
    print(f"File downloaded: {file_name}")
    
    try:
        # Tentukan jenis file dan baca datanya
        if file_name.endswith('.csv'):
            data = pd.read_csv(file_name, header=None)
            phone_numbers = data[0].tolist()  # Ambil nomor telepon dari kolom pertama
        elif file_name.endswith('.txt'):
            with open(file_name, 'r') as f:
                phone_numbers = [line.strip() for line in f.readlines() if line.strip()]
        elif file_name.endswith('.xls') or file_name.endswith('.xlsx'):
            data = pd.read_excel(file_name, header=None)
            phone_numbers = data[0].tolist()  # Ambil nomor telepon dari kolom pertama
        else:
            await update.message.reply_text("Format file tidak didukung. Kirim file CSV, TXT, atau Excel.")
            print(f"Unsupported file format: {file_name}")
            return ConversationHandler.END
        
        # Simpan nomor telepon di user_data
        user_data[update.message.chat.id] = phone_numbers
        print(f"Phone numbers saved for chat ID {update.message.chat.id}")
        
        # Minta nama dasar untuk kontak (base name)
        await update.message.reply_text("Masukkan nama dasar yang ingin digunakan untuk kontak (contoh: 'Kontak', bot akan menambah angka di belakangnya):")
    finally:
        # Hapus file setelah dibaca
        if os.path.exists(file_name):
            os.remove(file_name)
            print(f"Temporary file removed: {file_name}")
    
    return ASK_BASE_NAME

async def ask_base_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received base name: {update.message.text}")
    # Simpan nama dasar yang diberikan pengguna
    base_name = update.message.text
    
    # Simpan nama dasar di user_data
    user_data[update.message.chat.id + "_base_name"] = base_name
    
    # Minta nama file VCF yang diinginkan
    await update.message.reply_text("Sekarang, masukkan nama file VCF yang diinginkan (tanpa ekstensi):")
    
    return ASK_FILENAME

async def ask_filename(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print(f"Received filename: {update.message.text}")
    # Simpan nama file VCF yang diberikan pengguna
    vcf_filename = update.message.text + ".vcf"
    
    # Ambil data nomor telepon dan nama dasar dari user_data
    phone_numbers = user_data.get(update.message.chat.id)
    base_name = user_data.get(update.message.chat.id + "_base_name")
    
    if not phone_numbers or not base_name:
        await update.message.reply_text("Terjadi kesalahan dalam data yang diterima.")
        print("Error: Missing phone numbers or base name.")
        return ConversationHandler.END
    
    # Konversi ke VCF
    convert_to_vcf(phone_numbers, base_name, vcf_filename)
    
    # Kirim file VCF ke pengguna
    with open(vcf_filename, 'rb') as vcf_file:
        await context.bot.send_document(chat_id=update.message.chat.id, document=InputFile(vcf_file, filename=vcf_filename))
    print(f"VCF file sent: {vcf_filename}")
    
    # Hapus file VCF setelah dikirim
    if os.path.exists(vcf_filename):
        os.remove(vcf_filename)
        print(f"VCF file removed after sending: {vcf_filename}")
    
    # Reset user_data untuk chat ini
    user_data.pop(update.message.chat.id, None)
    user_data.pop(update.message.chat.id + "_base_name", None)
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    print("Process cancelled")
    await update.message.reply_text("Proses dibatalkan.")
    return ConversationHandler.END

async def main():
    print("Starting bot")
    # Buat instance aplikasi
    application = Application.builder().token(TOKEN).build()

    # Conversation handler untuk menangani alur percakapan
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Document.ALL, handle_document)],
        states={
            ASK_BASE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_base_name)],
            ASK_FILENAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_filename)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )
    
    # Tambahkan handler percakapan ke application
    application.add_handler(conv_handler)

    # Command /start
    application.add_handler(CommandHandler("start", start))

    # Inisialisasi aplikasi
    await application.initialize()

    # Menjalankan polling
    await application.start()
    await application.updater.start_polling()

if __name__ == '__main__':
    asyncio.run(main())
