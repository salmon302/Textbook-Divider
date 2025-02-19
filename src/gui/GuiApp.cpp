#include "GuiApp.h"
#include "imgui.h"
#include "imgui_impl_glfw.h"
#include "imgui_impl_opengl3.h"
#include <nfd.hpp>
#include <stdexcept>

GuiApp::GuiApp() : window(nullptr), processing(false), progress(0.0f),
	enableOCR(false), selectedLanguage("eng"), enableGPU(false) {
	if (!setupGLFW()) {
		throw std::runtime_error("Failed to initialize GLFW");
	}
	setupImGui();
	
	if (NFD::Init() != NFD_OKAY) {
		throw std::runtime_error("Failed to initialize NFD");
	}
	
	ocrProcessor = std::make_unique<OCRWrapper>();
	if (!ocrProcessor->initialize(selectedLanguage, enableGPU)) {
		throw std::runtime_error("Failed to initialize OCR");
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
	ImGui::SetNextWindowPos(ImVec2(0, 0));
	ImGui::SetNextWindowSize(ImGui::GetIO().DisplaySize);
	ImGui::Begin("Textbook Divider", nullptr, 
		ImGuiWindowFlags_NoTitleBar | ImGuiWindowFlags_NoResize | ImGuiWindowFlags_NoMove);

	if (ImGui::Button("Select Input File")) {
		NFD::UniquePath outPath;
		nfdfilteritem_t filterItem[3] = {
			{ "PDF", "pdf" },
			{ "EPUB", "epub" },
			{ "Text", "txt" }
		};
		nfdresult_t result = NFD::OpenDialog(outPath, filterItem, 3);
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
			}
			
			processing = false;
		}
	}

	ImGui::ProgressBar(progress);
	ImGui::Text("%s", statusMessage.c_str());

	if (!chapterList.empty()) {
		ImGui::BeginChild("Chapters", ImVec2(0, 200), true);
		for (const auto& chapter : chapterList) {
			ImGui::Text("%s", chapter.c_str());
		}
		ImGui::EndChild();
	}

	ImGui::End();
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