#include "ChapterDetector.h"
#include <sstream>
#include <iostream>
#include <algorithm>
#include <cmath>

ChapterDetector::ChapterDetector() {
	// Initialize chapter patterns with confidence scores
	patterns = {
		{std::regex(R"(Chapter\s+(\d+)\s*[:.-]\s*(.*))", std::regex::icase), 1.0f},
		{std::regex(R"((\d+)\.\s+(.*?))", std::regex::icase), 0.8f},
		{std::regex(R"(Part\s+(\d+)\s*[:.-]\s*(.*))", std::regex::icase), 0.7f},
		{std::regex(R"(^([IVXLCDM]+)\.\s+(.*?))", std::regex::icase), 0.6f}
	};
	
	// Initialize subchapter pattern
	subChapterPattern = std::regex(R"((\d+)\.(\d+)\s+(.*?))", std::regex::icase);
}

std::vector<Chapter> ChapterDetector::detectChapters(const std::string& content) {
	if (content.empty()) return {};
	
	// Split content into chunks for parallel processing
	auto chunks = splitContentIntoChunks(content, threadCount);
	std::vector<std::future<std::vector<Chapter>>> futures;
	std::vector<Chapter> allChapters;
	
	// Process chunks in parallel
	for (size_t i = 0; i < chunks.size(); ++i) {
		futures.push_back(std::async(std::launch::async,
			&ChapterDetector::processContentChunk, this, chunks[i], i * 1000));
	}
	
	// Collect results
	for (auto& future : futures) {
		auto chapters = future.get();
		mergeChapters(allChapters, chapters);
	}
	
	return allChapters;
}

std::vector<std::string> ChapterDetector::splitContentIntoChunks(const std::string& content, size_t chunkCount) {
	std::vector<std::string> chunks;
	std::istringstream stream(content);
	std::string line;
	std::vector<std::string> lines;
	
	while (std::getline(stream, line)) {
		lines.push_back(line);
	}
	
	size_t linesPerChunk = lines.size() / chunkCount;
	if (linesPerChunk == 0) linesPerChunk = 1;
	
	std::string currentChunk;
	size_t lineCount = 0;
	
	for (const auto& line : lines) {
		currentChunk += line + "\n";
		lineCount++;
		
		if (lineCount >= linesPerChunk && chunks.size() < chunkCount - 1) {
			chunks.push_back(currentChunk);
			currentChunk.clear();
			lineCount = 0;
		}
	}
	
	if (!currentChunk.empty()) {
		chunks.push_back(currentChunk);
	}
	
	return chunks;
}

std::vector<Chapter> ChapterDetector::processContentChunk(const std::string& chunk, size_t startLine) {
	std::vector<Chapter> chapters;
	std::istringstream stream(chunk);
	std::string line;
	
	Chapter currentChapter{0, "", "", 0.0f, false, 0, 0, 0.0f};
	std::string buffer;
	bool inChapter = false;
	
	while (std::getline(stream, line)) {
		int chapterNum;
		std::string title;
		float confidence;
		
		if (isChapterStart(line, chapterNum, title, confidence)) {
			if (inChapter && currentChapter.number > 0) {
				currentChapter.content = buffer;
				currentChapter.content_length = buffer.length();
				if (validateChapter(currentChapter, chapters)) {
					chapters.push_back(currentChapter);
				}
			}
			
			currentChapter = Chapter{chapterNum, cleanTitle(title), "", confidence, false, 0, 0, 0.0f};
			buffer.clear();
			inChapter = true;
		} else if (detectSubChapter(line, chapterNum, title)) {
			if (inChapter && !buffer.empty()) {
				Chapter subChapter{chapterNum, cleanTitle(title), buffer, 0.9f, true, currentChapter.number, buffer.length(), 0.0f};
				if (validateChapter(subChapter, chapters)) {
					chapters.push_back(subChapter);
				}
				buffer.clear();
			}
		} else if (inChapter) {
			buffer += line + "\n";
		}
	}
	
	if (inChapter && currentChapter.number > 0) {
		currentChapter.content = buffer;
		currentChapter.content_length = buffer.length();
		if (validateChapter(currentChapter, chapters)) {
			chapters.push_back(currentChapter);
		}
	}
	
	return chapters;
}

void ChapterDetector::mergeChapters(std::vector<Chapter>& main, const std::vector<Chapter>& additional) {
	for (const auto& chapter : additional) {
		bool shouldAdd = true;
		
		// Check for duplicates and overlaps
		for (const auto& existing : main) {
			if (chapter.number == existing.number) {
				// Keep the one with higher confidence
				if (chapter.confidence > existing.confidence) {
					shouldAdd = true;
					break;
				} else {
					shouldAdd = false;
					break;
				}
			}
		}
		
		if (shouldAdd) {
			main.push_back(chapter);
		}
	}
	
	// Sort chapters by number
	std::sort(main.begin(), main.end(), 
		[](const Chapter& a, const Chapter& b) { return a.number < b.number; });
}

bool ChapterDetector::isChapterStart(const std::string& line, int& chapterNum, std::string& title, float& confidence) {
	for (const auto& [pattern, conf] : patterns) {
		std::smatch matches;
		if (std::regex_search(line, matches, pattern)) {
			try {
				std::string numStr = matches[1].str();
				if (std::regex_match(numStr, std::regex("^[IVXLCDM]+$", std::regex::icase))) {
					numStr = convertRomanToArabic(numStr);
				} else {
					auto it = commonWords.find(numStr);
					if (it != commonWords.end()) {
						numStr = it->second;
					}
				}
				
				chapterNum = std::stoi(numStr);
				title = matches[2].str();
				confidence = conf * calculateConfidence(line, matches);
				return true;
			} catch (const std::exception& e) {
				std::cerr << "Error parsing chapter number: " << e.what() << std::endl;
			}
		}
	}
	return false;
}

bool ChapterDetector::validateChapter(const Chapter& chapter, const std::vector<Chapter>& existing) {
	if (chapter.content_length < minChapterLength) {
		return false;
	}
	
	for (const auto& existing_chapter : existing) {
		float similarity = calculateSimilarity(chapter.content, existing_chapter.content);
		if (similarity > maxSimilarity) {
			return false;
		}
	}
	
	return true;
}

float ChapterDetector::calculateSimilarity(const std::string& text1, const std::string& text2) {
	// Simple Jaccard similarity implementation
	std::istringstream stream1(text1), stream2(text2);
	std::unordered_map<std::string, bool> words;
	std::string word;
	int common = 0, total = 0;
	
	while (stream1 >> word) {
		words[word] = true;
		total++;
	}
	
	while (stream2 >> word) {
		if (words[word]) common++;
		total++;
	}
	
	return common > 0 ? static_cast<float>(common) / total : 0.0f;
}

std::string ChapterDetector::convertRomanToArabic(const std::string& roman) {
	static const std::unordered_map<char, int> values = {
		{'I', 1}, {'V', 5}, {'X', 10}, {'L', 50},
		{'C', 100}, {'D', 500}, {'M', 1000}
	};
	
	int result = 0;
	std::string upper = roman;
	std::transform(upper.begin(), upper.end(), upper.begin(), ::toupper);
	
	for (size_t i = 0; i < upper.length(); i++) {
		if (i + 1 < upper.length() && values.at(upper[i]) < values.at(upper[i + 1])) {
			result -= values.at(upper[i]);
		} else {
			result += values.at(upper[i]);
		}
	}
	
	return std::to_string(result);
}

float ChapterDetector::calculateConfidence(const std::string& line, const std::smatch& matches) {
	float confidence = 1.0f;
	
	// Reduce confidence for very short titles
	if (matches[2].length() < 3) confidence *= 0.7f;
	
	// Reduce confidence for unusually long chapter numbers
	if (matches[1].length() > 3) confidence *= 0.8f;
	
	// Boost confidence for standard "Chapter X" format
	if (line.find("Chapter") != std::string::npos) confidence *= 1.2f;
	
	return std::min(confidence, 1.0f);
}

bool ChapterDetector::detectSubChapter(const std::string& line, int& chapterNum, std::string& title) {
	std::smatch matches;
	if (std::regex_search(line, matches, subChapterPattern)) {
		try {
			chapterNum = std::stoi(matches[1].str()) * 100 + std::stoi(matches[2].str());
			title = matches[3].str();
			return true;
		} catch (const std::exception& e) {
			std::cerr << "Error parsing subchapter number: " << e.what() << std::endl;
		}
	}
	return false;
}

std::string ChapterDetector::cleanTitle(const std::string& title) {
	std::string cleaned = title;
	cleaned.erase(0, cleaned.find_first_not_of(" \t\n\r:"));
	cleaned.erase(cleaned.find_last_not_of(" \t\n\r:") + 1);
	return cleaned;
}