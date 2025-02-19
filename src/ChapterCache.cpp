#include "ChapterCache.h"
#include <functional>
#include <iomanip>
#include <sstream>
#include <algorithm>

ChapterCacheManager::ChapterCacheManager(size_t maxSize, std::chrono::minutes expiration)
	: maxCacheSize(maxSize), cacheExpiration(expiration) {}

std::string ChapterCacheManager::calculateHash(const std::string& content) {
	std::hash<std::string> hasher;
	size_t hash = hasher(content);
	std::stringstream ss;
	ss << std::hex << std::setw(16) << std::setfill('0') << hash;
	return ss.str();
}

void ChapterCacheManager::cleanExpired() {
	auto now = std::chrono::system_clock::now();
	for (auto it = cache.begin(); it != cache.end();) {
		if (now - it->second.timestamp > cacheExpiration) {
			it = cache.erase(it);
		} else {
			++it;
		}
	}
	
	while (cache.size() > maxCacheSize) {
		auto oldest = std::min_element(cache.begin(), cache.end(),
			[](const auto& a, const auto& b) {
				return a.second.timestamp < b.second.timestamp;
			});
		cache.erase(oldest);
	}
}

bool ChapterCacheManager::tryGet(const std::string& content, std::vector<Chapter>& chapters) {
	cleanExpired();
	std::string hash = calculateHash(content);
	auto it = cache.find(hash);
	if (it != cache.end()) {
		chapters = it->second.chapters;
		return true;
	}
	return false;
}

void ChapterCacheManager::update(const std::string& content, const std::vector<Chapter>& chapters) {
	std::string hash = calculateHash(content);
	ChapterCache cacheEntry{
		chapters,
		std::chrono::system_clock::now(),
		hash
	};
	cache[hash] = cacheEntry;
	cleanExpired();
}

void ChapterCacheManager::clear() {
	cache.clear();
}