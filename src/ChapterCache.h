#pragma once
#include <string>
#include <vector>
#include <unordered_map>
#include <chrono>
#include "ChapterDetector.h"

struct ChapterCache {
	std::vector<Chapter> chapters;
	std::chrono::system_clock::time_point timestamp;
	std::string contentHash;
};

class ChapterCacheManager {
public:
	ChapterCacheManager(size_t maxSize = 100, std::chrono::minutes expiration = std::chrono::minutes(30));
	
	bool tryGet(const std::string& content, std::vector<Chapter>& chapters);
	void update(const std::string& content, const std::vector<Chapter>& chapters);
	void clear();
	
private:
	std::string calculateHash(const std::string& content);
	void cleanExpired();
	
	std::unordered_map<std::string, ChapterCache> cache;
	size_t maxCacheSize;
	std::chrono::minutes cacheExpiration;
};