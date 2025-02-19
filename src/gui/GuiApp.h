#pragma once

#include <GLFW/glfw3.h>
#include <string>
#include "../FileHandler.h"
#include "../ChapterDetector.h"
#include "../TextProcessor.h"
#include "../OCRWrapper.h"

class GuiApp {
public:
	GuiApp();
	~GuiApp();
	
	void run();
	
private:
	GLFWwindow* window;
	bool setupGLFW();
	void setupImGui();
	void cleanup();
	void renderUI();
	
	// Application state
	std::string inputPath;
	std::string outputPath;
	bool processing;
	float progress;
	std::vector<std::string> chapterList;
	std::string statusMessage;
	bool enableOCR;
	std::string selectedLanguage;
	bool enableGPU;
	
	// Core components
	FileHandler fileHandler;
	ChapterDetector chapterDetector;
	TextProcessor textProcessor;
	std::unique_ptr<OCRWrapper> ocrProcessor;
	
	void processWithOCR();
};