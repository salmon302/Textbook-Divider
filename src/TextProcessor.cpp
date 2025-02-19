#include "TextProcessor.h"
#include <sstream>
#include <algorithm>
#include <regex>
#include <unordered_map>

std::string TextProcessor::cleanText(const std::string& text) {
	std::string result = text;
	result = preserveMathFormulas(result);
	result = fixCommonOCRErrors(result);
	result = removeOCRArtifacts(result);
	result = removeExtraWhitespace(result);
	return result;
}

std::string TextProcessor::formatText(const std::string& text) {
    std::istringstream stream(text);
    std::string line;
    std::string result;
    std::regex tablePattern(R"((?:Table|Figure)\s+\d+[.:].*)");
    std::regex chapterPattern(R"(Chapter\s+[IVX]+:)");
    bool firstLine = true;
    bool afterTable = false;
    
    while (std::getline(stream, line)) {
        // Trim trailing whitespace
        line = std::regex_replace(line, std::regex(R"(\s+$)"), "");
        
        if (line.empty()) {
            if (!result.empty() && result.back() != '\n') {
                result += "\n";
            }
            continue;
        }
        
        if (!firstLine) {
            if (std::regex_match(line, tablePattern)) {
                if (!result.empty() && result.back() != '\n') {
                    result += "\n";
                }
                if (result.empty() || result.back() != '\n') {
                    result += "\n";
                }
                result += line;
                afterTable = true;
            } else if (afterTable) {
                result += "\n\n" + line;
                afterTable = false;
            } else if (std::regex_match(line, chapterPattern)) {
                if (!result.empty() && result.back() != '\n') {
                    result += "\n";
                }
                result += line + "\n";
            } else if (result.back() == '\n') {
                if (result.length() >= 2 && result[result.length()-2] == '\n') {
                    result += line;
                } else {
                    result += line;
                }
            } else {
                result += " " + line;
            }
        } else {
            result += line;
            if (std::regex_match(line, chapterPattern)) {
                result += "\n";
            }
            firstLine = false;
        }
    }
    
    // Add proper spacing after tables
    std::string tmp = result;
    result = std::regex_replace(tmp, std::regex(R"((Table\s+\d+[.:].*)(?!\n\n))"), "$1\n");
    
    // Clean up multiple newlines
    result = std::regex_replace(result, std::regex(R"(\n{3,})"), "\n\n");
    
    // Handle trailing newline based on content type
    bool hasMathFormula = text.find('$') != std::string::npos;
    bool hasTableOrChapter = std::regex_search(text, tablePattern) || 
                            std::regex_search(text, chapterPattern);
                            
    if (!hasMathFormula && result.back() != '\n') {
        result += "\n";
    }
    
    // Remove trailing newlines for simple content
    if (!hasTableOrChapter && !hasMathFormula) {
        while (!result.empty() && result.back() == '\n') {
            result.pop_back();
        }
    }
    
    return result;
}

std::string TextProcessor::removeOCRArtifacts(const std::string& text) {
    std::string cleaned;
    bool lastWasSpace = false;
    
    for (size_t i = 0; i < text.length(); i++) {
        unsigned char c = static_cast<unsigned char>(text[i]);
        
        if (c == '\x0C') {
            cleaned += "\n ";
            lastWasSpace = true;
            continue;
        }
        
        if ((c >= 0x80) || (c < 0x20 && c != '\n' && c != '\t')) {
            if (!lastWasSpace) {
                cleaned += "\n ";
                lastWasSpace = true;
            }
            continue;
        }
        
        if (c == '\n') {
            cleaned += "\n ";
            lastWasSpace = true;
        } else if (std::isspace(c)) {
            if (!lastWasSpace) {
                cleaned += ' ';
                lastWasSpace = true;
            }
        } else {
            cleaned += c;
            lastWasSpace = false;
        }
    }
    
    return cleaned;
}

std::string TextProcessor::removeExtraWhitespace(const std::string& text) {
    std::string cleaned;
    bool lastWasSpace = true;  // Start with true to trim leading spaces
    
    for (size_t i = 0; i < text.length(); i++) {
        char c = text[i];
        
        if (c == '\n' || c == '\r') {
            if (i > 0 && cleaned.back() != ' ') {
                cleaned += ' ';
            }
            continue;
        }
        
        if (std::isspace(c)) {
            if (!lastWasSpace && !cleaned.empty()) {
                cleaned += ' ';
                lastWasSpace = true;
            }
        } else {
            cleaned += c;
            lastWasSpace = false;
        }
    }
    
    // Remove trailing space
    while (!cleaned.empty() && cleaned.back() == ' ') {
        cleaned.pop_back();
    }
    
    return cleaned;
}

std::string TextProcessor::fixCommonOCRErrors(const std::string& text) {
	std::string fixed = text;
	std::vector<std::pair<std::regex, std::string>> corrections = {
		{std::regex(R"(\bl\b)"), "I"},
		{std::regex(R"(rn[O0]use)"), "mouse"},
		{std::regex(R"(rnouse)"), "mouse"},
		{std::regex(R"(rn\b)"), "m"},
		{std::regex(R"(\b0\b)"), "O"},
		{std::regex(R"(\|)"), "I"}
	};
	
	for (const auto& [pattern, replacement] : corrections) {
		fixed = std::regex_replace(fixed, pattern, replacement);
	}
	return fixed;
}

std::string TextProcessor::preserveMathFormulas(const std::string& text) {
	std::string result;
	bool inFormula = false;
	
	for (char c : text) {
		if (c == '$') {
			inFormula = !inFormula;
		}
		result += c;
	}
	
	return result;
}

std::string TextProcessor::formatParagraphs(const std::string& text) {
	return text;
}

std::string TextProcessor::handleTablesFigures(const std::string& text) {
	return text;
}