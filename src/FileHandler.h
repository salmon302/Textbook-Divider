#pragma once
#include <string>
#include <vector>
#include <filesystem>
#include <fstream>
#include <stdexcept>

namespace fs = std::filesystem;

class FileHandler {
public:
	enum class FileType {
		PDF,
		EPUB,
		TXT,
		IMAGE,
		UNKNOWN
	};

	FileHandler() = default;
	~FileHandler() = default;

	// Main interface methods
	bool openFile(const std::string& filePath);
	bool saveChapter(const std::string& content, const std::string& outputPath, int chapterNum);
	std::string readContent();

	// OCR support methods
	bool isImageFile(const std::string& filePath) const;
	bool isPDFFile(const std::string& filePath) const;
	std::vector<std::string> extractPDFImages(const std::string& pdfPath);

private:
	FileType detectFileType(const std::string& filePath);
	std::string readPDF();
	std::string readEPUB();
	std::string readTXT();
	std::string readImage();

	fs::path currentFile;
	FileType currentFileType{FileType::UNKNOWN};
	std::string fileContent;

	// Image file extensions
	const std::vector<std::string> imageExtensions{".png", ".jpg", ".jpeg", ".tiff", ".bmp"};
};