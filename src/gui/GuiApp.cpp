#include "GuiApp.h"
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <nfd.hpp>
#include <stdexcept>
#include <cstdlib>

GuiApp::GuiApp() : window(nullptr), processing(false), progress(0.0f),
	enableOCR(false), selectedLanguage("eng"), enableGPU(false),
	currentChapter(-1), showSettings(false) {
	// Initialize detection settings
	detectionSettings = {
		1000.0f,  // minChapterLength
		10,       // minTitleLength
		true,     // detectSubchapters
		0.75f     // confidenceThreshold
	};
	if (!setupGLFW()) {
		throw std::runtime_error("Failed to initialize GLFW");
	}
	setupImGui();
	
	if (NFD::Init() != NFD_OKAY) {
		throw std::runtime_error("Failed to initialize NFD");
	}

	// Check external dependencies (once)
	depsChecked = true;
	depsOK = checkDependencies();
	
	ocrProcessor = std::make_unique<OCRWrapper>();
	if (!ocrProcessor->initialize(selectedLanguage, enableGPU)) {
		showError = true;
		errorMessage = "Failed to initialize OCR. Ensure Python, pytesseract, and dependencies are available.";
	}
	
	statusMessage = "Ready";
}

GuiApp::~GuiApp() {
	NFD::Quit();
	cleanup();
}

bool GuiApp::setupGLFW() {
	if (!glfwInit()) return false;
	
	glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
	glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
	window = glfwCreateWindow(800, 600, "Textbook Divider", nullptr, nullptr);
	
	if (!window) {
		glfwTerminate();
		return false;
	}
	
	glfwMakeContextCurrent(window);
	glfwSwapInterval(1);
	return true;
}

void GuiApp::setupImGui() {
	IMGUI_CHECKVERSION();
	ImGui::CreateContext();
	ImGui_ImplGlfw_InitForOpenGL(window, true);
	ImGui_ImplOpenGL3_Init("#version 130");
	ImGui::StyleColorsDark();
}

void GuiApp::cleanup() {
	ImGui_ImplOpenGL3_Shutdown();
	ImGui_ImplGlfw_Shutdown();
	ImGui::DestroyContext();
	if (window) {
		glfwDestroyWindow(window);
	}
	glfwTerminate();
}

void GuiApp::renderUI() {
	// Main window using the entire viewport
	ImGui::SetNextWindowPos(ImVec2(0, 0));
	ImGui::SetNextWindowSize(ImGui::GetIO().DisplaySize);
	ImGui::Begin("Textbook Divider", nullptr, 
		ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove | ImGuiWindowFlags_NoCollapse);

	// Left panel (controls)
	ImGui::BeginChild("LeftPanel", ImVec2(250, -1), true);
	renderSidebar();
	ImGui::EndChild();

	ImGui::SameLine();

	// Right panel (chapters and preview)
	ImGui::BeginChild("RightPanel", ImVec2(0, -1), true);
	renderMainContent();
	ImGui::EndChild();

	// Settings window (floating)
	if (showSettings)
		renderSettings();

	// Error modal overlay
	renderErrorModal();

	ImGui::End();
}

void GuiApp::renderSidebar() {
	if (ImGui::Button("Select Input File")) {

		NFD::UniquePath outPath;
		nfdfilteritem_t filterItem[2] = {
			{ "PDF", "pdf" },
			{ "Text", "txt" }
		};
		nfdresult_t result = NFD::OpenDialog(outPath, filterItem, 2);
		if (result == NFD_OKAY) {
			inputPath = outPath.get();
		}
	}
	ImGui::SameLine();
	ImGui::Text("%s", inputPath.empty() ? "No file selected" : inputPath.c_str());

	if (ImGui::Button("Select Output Directory")) {
		NFD::UniquePath outPath;
		nfdresult_t result = NFD::PickFolder(outPath);
		if (result == NFD_OKAY) {
			outputPath = outPath.get();
		}
	}
	ImGui::SameLine();
	ImGui::Text("%s", outputPath.empty() ? "No directory selected" : outputPath.c_str());

	// Add OCR settings
	if (ImGui::CollapsingHeader("OCR Settings")) {
		ImGui::Checkbox("Enable OCR", &enableOCR);
		
		if (enableOCR) {
			const char* languages[] = { "eng", "fra", "deu", "spa", "ita" };
			const char* langNames[] = { "English", "French", "German", "Spanish", "Italian" };
			
			if (ImGui::BeginCombo("Language", selectedLanguage.c_str())) {
				for (int i = 0; i < IM_ARRAYSIZE(languages); i++) {
					bool isSelected = (selectedLanguage == languages[i]);
					if (ImGui::Selectable(langNames[i], isSelected)) {
						selectedLanguage = languages[i];
						ocrProcessor->initialize(selectedLanguage, enableGPU);
					}
					if (isSelected) {
						ImGui::SetItemDefaultFocus();
					}
				}
				ImGui::EndCombo();
			}
			
			if (ImGui::Checkbox("Enable GPU", &enableGPU)) {
				ocrProcessor->initialize(selectedLanguage, enableGPU);
			}
		}
	}

	if (!inputPath.empty() && !outputPath.empty()) {
		if (!processing && ImGui::Button("Process Textbook")) {
			if (!depsOK) {
				showError = true;
				errorMessage = "Missing dependencies. Please install Poppler (pdftoppm) and ensure it is in PATH.";
				return;
			}
			processing = true;
			progress = 0.0f;
			chapterList.clear();
			
			try {
				if (enableOCR) {
					processWithOCR();
				} else {
					if (!fileHandler.openFile(inputPath)) {
						throw std::runtime_error("Could not open input file");
					}
					
					std::string content = fileHandler.readContent();
					progress = 0.3f;
					
					content = textProcessor.cleanText(content);
					content = textProcessor.formatText(content);
					progress = 0.6f;
					
					auto chapters = chapterDetector.detectChapters(content);
					if (chapters.empty()) {
						throw std::runtime_error("No chapters detected");
					}
					
					for (const auto& chapter : chapters) {
						if (!fileHandler.saveChapter(chapter.content, outputPath, chapter.number)) {
							throw std::runtime_error("Failed to save chapter " + std::to_string(chapter.number));
						}
						chapterList.push_back("Chapter " + std::to_string(chapter.number) + ": " + chapter.title);
					}
					
					progress = 1.0f;
					statusMessage = "Processing complete!";
				}
			} catch (const std::exception& e) {
				statusMessage = "Error: ";
				statusMessage += e.what();
				showError = true;
				errorMessage = statusMessage;
			}
			
			processing = false;
		}
	}

	ImGui::ProgressBar(progress);
	ImGui::Text("%s", statusMessage.c_str());
}


void GuiApp::renderMainContent() {
	// Chapter list on the left side of the right panel
	ImGui::BeginChild("ChapterList", ImVec2(200, 0), true);

	for (size_t i = 0; i < chapterList.size(); i++) {
		if (ImGui::Selectable(chapterList[i].c_str(), currentChapter == i)) {
			currentChapter = i;
			updateChapterPreview();
		}
	}
	ImGui::EndChild();
	
	ImGui::SameLine();
	
	// Chapter preview on the right
	ImGui::BeginChild("Preview", ImVec2(0, 0), true);
	if (currentChapter >= 0 && currentChapter < chapterList.size()) {
		ImGui::TextWrapped("%s", previewContent.c_str());
	} else {
		ImGui::TextWrapped("Select a chapter to preview its content");
	}
	ImGui::EndChild();
}


void GuiApp::renderSettings() {
	ImGui::SetNextWindowSize(ImVec2(400, 400), ImGuiCond_FirstUseEver);
	ImGui::Begin("Settings", &showSettings, ImGuiWindowFlags_NoCollapse);
	
	if (ImGui::CollapsingHeader("OCR Settings")) {
		ImGui::Checkbox("Enable OCR", &enableOCR);
		if (enableOCR) {
			const char* languages[] = { "eng", "fra", "deu", "spa", "ita" };
			const char* langNames[] = { "English", "French", "German", "Spanish", "Italian" };
			
			if (ImGui::BeginCombo("Language", selectedLanguage.c_str())) {
				for (int i = 0; i < IM_ARRAYSIZE(languages); i++) {
					bool isSelected = (selectedLanguage == languages[i]);
					if (ImGui::Selectable(langNames[i], isSelected)) {
						selectedLanguage = languages[i];
						ocrProcessor->initialize(selectedLanguage, enableGPU);
					}
					if (isSelected) {
						ImGui::SetItemDefaultFocus();
					}
				}
				ImGui::EndCombo();
			}
			
			if (ImGui::Checkbox("Enable GPU", &enableGPU)) {
				ocrProcessor->initialize(selectedLanguage, enableGPU);
			}
		}
	}
	
	if (ImGui::CollapsingHeader("Chapter Detection")) {
		ImGui::SliderFloat("Min Chapter Length", &detectionSettings.minChapterLength, 100.0f, 5000.0f);
		ImGui::SliderInt("Min Title Length", &detectionSettings.minTitleLength, 5, 50);
		ImGui::Checkbox("Detect Subchapters", &detectionSettings.detectSubchapters);
		ImGui::SliderFloat("Confidence Threshold", &detectionSettings.confidenceThreshold, 0.0f, 1.0f);
	}
	
	ImGui::End();
}

void GuiApp::updateChapterPreview() {
	if (currentChapter >= 0 && currentChapter < chapterList.size()) {
		// Load chapter content from file
		std::string chapterPath = outputPath + "/chapter_" + std::to_string(currentChapter + 1) + ".txt";
		previewContent = fileHandler.readFile(chapterPath);
	}
}

void GuiApp::run() {
	while (!glfwWindowShouldClose(window)) {
		glfwPollEvents();
		
		ImGui_ImplOpenGL3_NewFrame();
		ImGui_ImplGlfw_NewFrame();
		ImGui::NewFrame();
		
		renderUI();
		
		ImGui::Render();
		int display_w, display_h;
		glfwGetFramebufferSize(window, &display_w, &display_h);
		glViewport(0, 0, display_w, display_h);
		glClear(GL_COLOR_BUFFER_BIT);
		ImGui_ImplOpenGL3_RenderDrawData(ImGui::GetDrawData());
		
		glfwSwapBuffers(window);
	}
}

void GuiApp::processWithOCR() {
	std::string content;
	if (fileHandler.isImageFile(inputPath)) {
		content = ocrProcessor->processImage(inputPath);
	} else if (fileHandler.isPDFFile(inputPath)) {
		auto images = fileHandler.extractPDFImages(inputPath);
		content = ocrProcessor->processImages(images);
	} else {
		throw std::runtime_error("File format not supported for OCR");
	}
	
	progress = 0.3f;
	
	content = textProcessor.cleanText(content);
	content = textProcessor.formatText(content);
	progress = 0.6f;
	
	auto chapters = chapterDetector.detectChapters(content);
	if (chapters.empty()) {
		throw std::runtime_error("No chapters detected");
	}
	
	for (const auto& chapter : chapters) {
		if (!fileHandler.saveChapter(chapter.content, outputPath, chapter.number)) {
			throw std::runtime_error("Failed to save chapter " + std::to_string(chapter.number));
		}
		chapterList.push_back("Chapter " + std::to_string(chapter.number) + ": " + chapter.title);
	}
	
	progress = 1.0f;
	statusMessage = "Processing complete!";
}

bool GuiApp::checkDependencies() {
	// Check for Poppler's pdftoppm (used by FileHandler::extractPDFImages)
#ifdef _WIN32
	const char* cmd = "where pdftoppm >nul 2>nul";
#else
	const char* cmd = "which pdftoppm >/dev/null 2>&1";
#endif
	int code = system(cmd);
	return code == 0;
}

void GuiApp::renderErrorModal() {
	if (showError) {
		ImGui::OpenPopup("Error");
	}
	if (ImGui::BeginPopupModal("Error", nullptr, ImGuiWindowFlags_AlwaysAutoResize)) {
		ImGui::TextWrapped("%s", errorMessage.c_str());
		ImGui::Separator();
		if (ImGui::Button("OK", ImVec2(120, 0))) {
			showError = false;
			ImGui::CloseCurrentPopup();
		}
		ImGui::EndPopup();
	}
}