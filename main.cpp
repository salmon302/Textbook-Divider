#include <iostream>
#include <filesystem>
#include "src/FileHandler.h"
#include "src/ChapterDetector.h"
#include "src/TextProcessor.h"

namespace fs = std::filesystem;

void printUsage() {
    std::cout << "Usage: textbook-divider <input_file> <output_directory>\n";
}

int main(int argc, char* argv[]) {
    if (argc != 3) {
        printUsage();
        return 1;
    }

    std::string inputPath = argv[1];
    std::string outputPath = argv[2];

    std::cout << "Input file: " << inputPath << std::endl;
    std::cout << "Output directory: " << outputPath << std::endl;

    // Initialize components
    FileHandler fileHandler;
    ChapterDetector chapterDetector;
    TextProcessor textProcessor;

    try {
        // Open and read input file
        std::cout << "Opening input file..." << std::endl;
        if (!fileHandler.openFile(inputPath)) {
            std::cerr << "Error: Could not open input file: " << inputPath << "\n";
            return 1;
        }
        std::cout << "File opened successfully." << std::endl;

        // Get content and process it
        std::cout << "Reading content..." << std::endl;
        std::string content = fileHandler.readContent();
        std::cout << "Content length: " << content.length() << " characters" << std::endl;
        
        std::cout << "Cleaning text..." << std::endl;
        content = textProcessor.cleanText(content);
        std::cout << "Formatting text..." << std::endl;
        content = textProcessor.formatText(content);

        // Detect chapters
        std::cout << "Detecting chapters..." << std::endl;
        auto chapters = chapterDetector.detectChapters(content);
        if (chapters.empty()) {
            std::cerr << "Warning: No chapters detected in the input file.\n";
            return 1;
        }

        // Save chapters
        std::cout << "Detected " << chapters.size() << " chapters.\n";
        for (const auto& chapter : chapters) {
            std::cout << "Processing Chapter " << chapter.number << ": " << chapter.title << "\n";
            if (!fileHandler.saveChapter(chapter.content, outputPath, chapter.number)) {
                std::cerr << "Error: Failed to save chapter " << chapter.number << "\n";
                return 1;
            }
        }

        std::cout << "Successfully processed all chapters.\n";
        return 0;

    } catch (const std::exception& e) {
        std::cerr << "Error: " << e.what() << "\n";
        return 1;
    }
}