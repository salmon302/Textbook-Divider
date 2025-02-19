#include "FileHandler.h"
#include <algorithm>
#include <fstream>
#include <sstream>
#include <podofo/podofo.h>
#include <cstdlib>

bool FileHandler::openFile(const std::string& filePath) {
	currentFile = fs::path(filePath);
	if (!fs::exists(currentFile)) {
		return false;
	}
	
	currentFileType = detectFileType(filePath);
	if (currentFileType == FileType::UNKNOWN) {
		return false;
	}
	
	fileContent = readContent();
	return !fileContent.empty();
}

bool FileHandler::isImageFile(const std::string& filePath) const {
	fs::path path(filePath);
	std::string ext = path.extension().string();
	std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
	return std::find(imageExtensions.begin(), imageExtensions.end(), ext) != imageExtensions.end();
}

bool FileHandler::isPDFFile(const std::string& filePath) const {
	fs::path path(filePath);
	std::string ext = path.extension().string();
	std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
	return ext == ".pdf";
}

std::vector<std::string> FileHandler::extractPDFImages(const std::string& pdfPath) {
	std::vector<std::string> imagePaths;
	fs::path tempDir = fs::temp_directory_path() / "textbook_divider_temp";
	fs::create_directories(tempDir);

	try {
		PoDoFo::PdfMemDocument document(pdfPath.c_str());
		int pageCount = document.GetPageCount();
		const int BATCH_SIZE = 10; // Process 10 pages at a time

		for (int batch = 0; batch < pageCount; batch += BATCH_SIZE) {
			int batchEnd = std::min(batch + BATCH_SIZE, pageCount);
			
			// Process batch of pages
			for (int i = batch; i < batchEnd; ++i) {
				std::string imagePath = (tempDir / ("page_" + std::to_string(i + 1) + ".png")).string();
				
				// Convert page to image using Poppler with resolution limit
				std::string cmd = "pdftoppm -png -r 300 -f " + std::to_string(i + 1) + 
								" -l " + std::to_string(i + 1) + " \"" + 
								pdfPath + "\" \"" + tempDir.string() + "/page\"";
				
				if (system(cmd.c_str()) == 0) {
					imagePaths.push_back(imagePath);
				}
			}
			
			// Clean up previous batch files except the last processed ones
			if (batch > 0) {
				for (int i = batch - BATCH_SIZE; i < batch; ++i) {
					fs::path oldFile = tempDir / ("page_" + std::to_string(i + 1) + ".png");
					if (fs::exists(oldFile)) {
						fs::remove(oldFile);
					}
				}
			}
		}
	} catch (const PoDoFo::PdfError& e) {
		// Clean up temp directory on error
		fs::remove_all(tempDir);
		throw std::runtime_error("Failed to process PDF: " + std::string(e.what()));
	}

	return imagePaths;
}

std::string FileHandler::readImage() {
	if (currentFileType != FileType::IMAGE) {
		throw std::runtime_error("Current file is not an image");
	}
	return ""; // Empty string as actual OCR is handled by OCRWrapper
}

FileHandler::FileType FileHandler::detectFileType(const std::string& filePath) {
	if (isImageFile(filePath)) return FileType::IMAGE;
	if (isPDFFile(filePath)) return FileType::PDF;
	
	fs::path path(filePath);
	std::string ext = path.extension().string();
	std::transform(ext.begin(), ext.end(), ext.begin(), ::tolower);
	
	if (ext == ".epub") return FileType::EPUB;
	if (ext == ".txt") return FileType::TXT;
	return FileType::UNKNOWN;
}

std::string FileHandler::readContent() {
	switch (currentFileType) {
		case FileType::PDF:
			return readPDF();
		case FileType::EPUB:
			return readEPUB();
		case FileType::TXT:
			return readTXT();
		case FileType::IMAGE:
			return readImage();
		default:
			return "";
	}
}

std::string FileHandler::readPDF() {
	try {
		PoDoFo::PdfMemDocument document(currentFile.string().c_str());
		std::stringstream textContent;
		
		int pageCount = document.GetPageCount();
		const int BATCH_SIZE = 20; // Process 20 pages at a time
		
		for (int batch = 0; batch < pageCount; batch += BATCH_SIZE) {
			int batchEnd = std::min(batch + BATCH_SIZE, pageCount);
			std::stringstream batchContent;
			
			for (int i = batch; i < batchEnd; ++i) {
				PoDoFo::PdfPage* page = document.GetPage(i);
				if (!page) continue;
				
				PoDoFo::PdfContentsTokenizer tokenizer(page);
				const char* token = nullptr;
				PoDoFo::PdfVariant variant;
				PoDoFo::EPdfContentsType type;
				
				std::string currentText;
				while (tokenizer.ReadNext(type, token, variant)) {
					if (type == PoDoFo::ePdfContentsType_Keyword && token) {
						if (strcmp(token, "TJ") == 0 || strcmp(token, "Tj") == 0) {
							if (!currentText.empty()) {
								batchContent << currentText << " ";
								currentText.clear();
							}
						}
					}
					else if (type == PoDoFo::ePdfContentsType_Variant && variant.IsString()) {
						currentText += variant.GetString().GetStringUtf8();
					}
				}
				batchContent << "\n\n";
			}
			
			textContent << batchContent.str();
			batchContent.str(""); // Clear batch content
		}
		
		return textContent.str();
	} catch (const PoDoFo::PdfError& e) {
		throw std::runtime_error("Failed to read PDF: " + std::string(e.what()));
	}
}

std::string FileHandler::readEPUB() {
	throw std::runtime_error("EPUB reading not yet implemented");

}

std::string FileHandler::readTXT() {
	std::ifstream file(currentFile, std::ios::binary);
	if (!file.is_open()) {
		return "";
	}
	
	std::stringstream buffer;
	buffer << file.rdbuf();
	return buffer.str();
}


bool FileHandler::saveChapter(const std::string& content, const std::string& outputPath, int chapterNum) {
	fs::path outDir(outputPath);
	if (!fs::exists(outDir)) {
		if (!fs::create_directories(outDir)) {
			return false;
		}
	}
	
	std::string filename = "chapter_" + std::to_string(chapterNum) + ".txt";
	fs::path outFile = outDir / filename;
	
	std::ofstream out(outFile);
	if (!out.is_open()) {
		return false;
	}
	
	out << content;
	return true;
}