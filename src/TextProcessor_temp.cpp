#include "TextProcessor.h"
#include <sstream>
#include <algorithm>
#include <regex>

std::string TextProcessor::removeOCRArtifacts(const std::string& text) {
	std::string cleaned;
	bool lastWasSpace = false;
	
	for (char c : text) {
		if (c == '\x0C') {
			cleaned += "\n ";
			lastWasSpace = true;
			continue;
		}
		
		if (c == '©' || c == '®' || c == '™' || (c < 0x20 && c != '\n') || c > 0x7E) {
			if (!lastWasSpace) {
				cleaned += ' ';
				lastWasSpace = true;
			}
			continue;
		}
		
		cleaned += c;
		lastWasSpace = std::isspace(c);
	}
	
	return cleaned;
}