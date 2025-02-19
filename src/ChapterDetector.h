#pragma once
#include <string>
#include <vector>
#include <regex>
#include <memory>
#include <unordered_map>
#include <future>
#include <thread>

struct Chapter {
	int number;
	std::string title;
	std::string content;
	float confidence;
	bool is_subchapter;
	int parent_chapter;
	size_t content_length;
	float similarity_score;
};

class ChapterDetector {
public:
	ChapterDetector();
	~ChapterDetector() = default;

	std::vector<Chapter> detectChapters(const std::string& content);
	void setCustomPattern(const std::string& pattern);
	void setMinimumChapterLength(size_t length) { minChapterLength = length; }
	void setMaxSimilarityThreshold(float threshold) { maxSimilarity = threshold; }
	void setThreadCount(size_t count) { threadCount = count; }

private:
	bool isChapterStart(const std::string& line, int& chapterNum, std::string& title, float& confidence);
	std::string cleanTitle(const std::string& title);
	bool validateChapter(const Chapter& chapter, const std::vector<Chapter>& existing);
	float calculateSimilarity(const std::string& text1, const std::string& text2);
	bool detectSubChapter(const std::string& line, int& chapterNum, std::string& title);
	std::string convertRomanToArabic(const std::string& roman);
	float calculateConfidence(const std::string& line, const std::smatch& matches);

	// Parallel processing methods
	std::vector<Chapter> processContentChunk(const std::string& chunk, size_t startLine);
	std::vector<std::string> splitContentIntoChunks(const std::string& content, size_t chunkCount);
	void mergeChapters(std::vector<Chapter>& main, const std::vector<Chapter>& additional);

	// Chapter patterns
	std::vector<std::pair<std::regex, float>> patterns;
	std::regex subChapterPattern;
	std::string customPattern;

	// Validation parameters
	size_t minChapterLength{500};  // Minimum chapter length in characters
	float maxSimilarity{0.8f};     // Maximum similarity threshold between chapters
	
	// Parallel processing parameters
	size_t threadCount{std::thread::hardware_concurrency()};

	// Common words for fuzzy matching
	std::unordered_map<std::string, std::string> commonWords{
		{"one", "1"}, {"two", "2"}, {"three", "3"},
		{"first", "1"}, {"second", "2"}, {"third", "3"}
	};
};