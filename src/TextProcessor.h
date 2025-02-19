#pragma once
#include <string>
#include <vector>
#include <regex>

class TextProcessor {
public:
	TextProcessor() = default;
	~TextProcessor() = default;

	// Main interface methods
	std::string cleanText(const std::string& text);
	std::string formatText(const std::string& text);

private:
	// Text cleaning methods
	std::string removeOCRArtifacts(const std::string& text);
	std::string removeExtraWhitespace(const std::string& text);
	std::string fixCommonOCRErrors(const std::string& text);
	std::string normalizeLineEndings(const std::string& text);
	
	// Text formatting methods
	std::string preserveMathFormulas(const std::string& text);
	std::string formatParagraphs(const std::string& text);
	std::string handleTablesFigures(const std::string& text);
};
