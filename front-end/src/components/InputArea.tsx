import React, { useState, useRef } from "react";
import { MaskingModal } from "./MaskingModal";

interface InputAreaProps {
  onSendMessage: (
    text: string,
    image: File | null,
    image2: File | null,
    image3: File | null,
    document: File | null,
    mask: File | null
  ) => void;
  onCancelResponse?: () => void;
  isLoading: boolean;
}

export const InputArea: React.FC<InputAreaProps> = ({
  onSendMessage,
  onCancelResponse,
  isLoading,
}) => {
  const [text, setText] = useState("");
  const [stagedImage, setStagedImage] = useState<File | null>(null);
  const [stagedImagePreview, setStagedImagePreview] = useState<string | null>(null);
  const [stagedImage2, setStagedImage2] = useState<File | null>(null);
  const [stagedImage2Preview, setStagedImage2Preview] = useState<string | null>(null);
  const [stagedImage3, setStagedImage3] = useState<File | null>(null);
  const [stagedImage3Preview, setStagedImage3Preview] = useState<string | null>(null);
  const [stagedDocument, setStagedDocument] = useState<File | null>(null);
  const [stagedMask, setStagedMask] = useState<File | null>(null);
  
  // Masking Modal states
  const [isMaskModalOpen, setIsMaskModalOpen] = useState(false);
  const [maskModalImage, setMaskModalImage] = useState<File | null>(null);
  const [isDragOver, setIsDragOver] = useState(false);

  const imageInputRef = useRef<HTMLInputElement>(null);
  const docInputRef = useRef<HTMLInputElement>(null);
  const maskBaseInputRef = useRef<HTMLInputElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const handleTextChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setText(e.target.value);
    // Auto-grow height
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = `${Math.min(
        textareaRef.current.scrollHeight,
        200
      )}px`;
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = e.target.files;
    if (files && files.length > 0) {
      if (files.length === 1) {
        if (!stagedImage) {
          stageImageFile(files[0], 1);
        } else if (!stagedImage2) {
          stageImageFile(files[0], 2);
        } else if (!stagedImage3) {
          stageImageFile(files[0], 3);
        } else {
          stageImageFile(files[0], 1);
        }
      } else {
        stageImageFile(files[0], 1);
        if (files[1]) stageImageFile(files[1], 2);
        if (files[2]) stageImageFile(files[2], 3);
      }
      clearStagedMask();
      if (imageInputRef.current) imageInputRef.current.value = "";
    }
  };

  const stageImageFile = (file: File, slot: 1 | 2 | 3 = 1) => {
    if (!file.type.startsWith("image/")) {
      alert("Please upload an image file (png, jpg, jpeg).");
      return;
    }
    const reader = new FileReader();
    reader.onloadend = () => {
      if (slot === 1) {
        setStagedImage(file);
        setStagedImagePreview(reader.result as string);
      } else if (slot === 2) {
        setStagedImage2(file);
        setStagedImage2Preview(reader.result as string);
      } else {
        setStagedImage3(file);
        setStagedImage3Preview(reader.result as string);
      }
    };
    reader.readAsDataURL(file);
  };

  // Masking upload triggers
  const handleMaskBaseChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      if (!file.type.startsWith("image/")) {
        alert("Please select an image file to paint a mask on.");
        return;
      }
      setMaskModalImage(file);
      setIsMaskModalOpen(true);
    }
  };

  const handleMaskSave = (maskBlob: Blob) => {
    if (!maskModalImage) return;

    // Convert Blob to File object
    const maskFile = new File([maskBlob], `mask_${maskModalImage.name}`, {
      type: "image/png",
    });

    setStagedImage(maskModalImage);
    setStagedMask(maskFile);

    // Set preview to base image
    const reader = new FileReader();
    reader.onloadend = () => {
      setStagedImagePreview(reader.result as string);
    };
    reader.readAsDataURL(maskModalImage);

    // Clean up modal states
    setIsMaskModalOpen(false);
    setMaskModalImage(null);
    if (maskBaseInputRef.current) maskBaseInputRef.current.value = "";
  };

  const handleDocChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (file) {
      stageDocFile(file);
    }
  };

  const stageDocFile = (file: File) => {
    const ext = file.name.split(".").pop()?.toLowerCase();
    if (ext !== "pdf" && ext !== "txt" && ext !== "docx") {
      alert("Please upload a PDF, DOCX or TXT document.");
      return;
    }
    setStagedDocument(file);
  };

  const clearStagedImage = () => {
    setStagedImage(null);
    setStagedImagePreview(null);
    clearStagedMask();
    if (imageInputRef.current) imageInputRef.current.value = "";
  };

  const clearStagedImage2 = () => {
    setStagedImage2(null);
    setStagedImage2Preview(null);
    if (imageInputRef.current) imageInputRef.current.value = "";
  };

  const clearStagedImage3 = () => {
    setStagedImage3(null);
    setStagedImage3Preview(null);
    if (imageInputRef.current) imageInputRef.current.value = "";
  };

  const clearStagedMask = () => {
    setStagedMask(null);
    if (maskBaseInputRef.current) maskBaseInputRef.current.value = "";
  };

  const clearStagedDocument = () => {
    setStagedDocument(null);
    if (docInputRef.current) docInputRef.current.value = "";
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(true);
  };

  const handleDragLeave = () => {
    setIsDragOver(false);
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    setIsDragOver(false);
    const files = Array.from(e.dataTransfer.files);

    // Find all images and first document
    const imageFiles = files.filter((f) => f.type.startsWith("image/"));
    const docFile = files.find((f) => {
      const ext = f.name.split(".").pop()?.toLowerCase();
      return ext === "pdf" || ext === "txt" || ext === "docx";
    });

    if (imageFiles.length > 0) {
      if (imageFiles.length === 1) {
        if (!stagedImage) {
          stageImageFile(imageFiles[0], 1);
        } else if (!stagedImage2) {
          stageImageFile(imageFiles[0], 2);
        } else if (!stagedImage3) {
          stageImageFile(imageFiles[0], 3);
        } else {
          stageImageFile(imageFiles[0], 1);
        }
      } else {
        stageImageFile(imageFiles[0], 1);
        if (imageFiles[1]) stageImageFile(imageFiles[1], 2);
        if (imageFiles[2]) stageImageFile(imageFiles[2], 3);
      }
      clearStagedMask();
    }
    if (docFile) stageDocFile(docFile);
  };

  const handleSubmit = () => {
    if (!text.trim() && !stagedImage && !stagedImage2 && !stagedImage3 && !stagedDocument) return;
    if (isLoading) return;

    onSendMessage(text, stagedImage, stagedImage2, stagedImage3, stagedDocument, stagedMask);
    setText("");
    clearStagedImage();
    clearStagedImage2();
    clearStagedImage3();
    clearStagedDocument();

    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
    }
  };

  const handleCancel = () => {
    if (onCancelResponse) {
      onCancelResponse();
    }
  };

  return (
    <div className="w-full max-w-4xl mx-auto px-4 pb-6">
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`relative rounded-2xl bg-slate-900 border transition-all duration-300 ${isDragOver
          ? "border-indigo-500 ring-2 ring-indigo-500/20 bg-slate-900/80"
          : "border-slate-800 focus-within:border-slate-700/80 shadow-[0_10px_30px_rgba(0,0,0,0.3)]"
          }`}
      >
        {/* Hidden inputs */}
        <input
          type="file"
          ref={imageInputRef}
          onChange={handleImageChange}
          accept="image/*"
          multiple
          className="hidden"
        />
        <input
          type="file"
          ref={docInputRef}
          onChange={handleDocChange}
          accept=".pdf,.txt,.docx"
          className="hidden"
        />
        <input
          type="file"
          ref={maskBaseInputRef}
          onChange={handleMaskBaseChange}
          accept="image/*"
          className="hidden"
        />

        {/* Thumbnail Previews Section */}
        {(stagedImagePreview || stagedImage2Preview || stagedImage3Preview || stagedDocument) && (
          <div className="flex flex-wrap items-center gap-3 p-4 border-b border-slate-800/80 bg-slate-950/40 rounded-t-2xl">
            {/* Image 1 Preview */}
            {stagedImagePreview && (
              <div className="relative group w-16 h-16 rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center">
                <img
                  src={stagedImagePreview}
                  alt="Staged reference 1"
                  className="w-full h-full object-cover"
                />
                {stagedMask && (
                  <div className="absolute inset-0 bg-red-500/20 flex items-center justify-center pointer-events-none">
                    <span className="bg-slate-950/90 text-[8px] text-red-400 font-bold px-1.5 py-0.5 rounded border border-red-500/30 uppercase tracking-wide">
                      Masked
                    </span>
                  </div>
                )}
                <div className="absolute bottom-1 left-1 bg-slate-950/80 text-slate-300 text-[8px] font-bold px-1.5 py-0.5 rounded border border-slate-800 leading-none">
                  Ref 1
                </div>
                <button
                  type="button"
                  onClick={clearStagedImage}
                  className="absolute top-1 right-1 bg-slate-950/80 text-slate-400 hover:text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-all border border-slate-800"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* Image 2 Preview */}
            {stagedImage2Preview && (
              <div className="relative group w-16 h-16 rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center">
                <img
                  src={stagedImage2Preview}
                  alt="Staged reference 2"
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-1 left-1 bg-slate-950/80 text-slate-300 text-[8px] font-bold px-1.5 py-0.5 rounded border border-slate-800 leading-none">
                  Ref 2
                </div>
                <button
                  type="button"
                  onClick={clearStagedImage2}
                  className="absolute top-1 right-1 bg-slate-950/80 text-slate-400 hover:text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-all border border-slate-800"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* Image 3 Preview */}
            {stagedImage3Preview && (
              <div className="relative group w-16 h-16 rounded-lg overflow-hidden border border-slate-800 bg-slate-950 flex items-center justify-center">
                <img
                  src={stagedImage3Preview}
                  alt="Staged reference 3"
                  className="w-full h-full object-cover"
                />
                <div className="absolute bottom-1 left-1 bg-slate-950/80 text-slate-300 text-[8px] font-bold px-1.5 py-0.5 rounded border border-slate-800 leading-none">
                  Ref 3
                </div>
                <button
                  type="button"
                  onClick={clearStagedImage3}
                  className="absolute top-1 right-1 bg-slate-950/80 text-slate-400 hover:text-white rounded-full p-1 opacity-0 group-hover:opacity-100 transition-all border border-slate-800"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3 h-3">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}

            {/* Document Chip */}
            {stagedDocument && (
              <div className="relative group flex items-center gap-2 px-3 py-2 rounded-lg border border-slate-800 bg-slate-950/80 text-xs text-slate-300">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-4 h-4 text-indigo-400">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m2.25 0H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
                </svg>
                <span className="font-semibold truncate max-w-[150px]">{stagedDocument.name}</span>
                <button
                  type="button"
                  onClick={clearStagedDocument}
                  className="bg-slate-900 text-slate-400 hover:text-white rounded-full p-0.5 border border-slate-800 ml-1"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-2.5 h-2.5">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            )}
          </div>
        )}

        {/* Text Area Input */}
        <div className="flex items-end gap-2 p-3">
          {/* File Attachment Triggers */}
          <div className="flex items-center gap-1.5 mb-1.5 pl-1.5">
            {/* Image Upload Button */}
            <button
              type="button"
              onClick={() => imageInputRef.current?.click()}
              disabled={isLoading}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="Upload Reference Image"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="m2.25 15.75 5.159-5.159a2.25 2.25 0 0 1 3.182 0l5.159 5.159m-1.5-1.5 1.409-1.409a2.25 2.25 0 0 1 3.182 0l2.909 2.909m-18 3.75h16.5a1.5 1.5 0 0 0 1.5-1.5V6a1.5 1.5 0 0 0-1.5-1.5H3.75A1.5 1.5 0 0 0 2.25 6v12a1.5 1.5 0 0 0 1.5 1.5Zm10.5-11.25h.008v.008h-.008V8.25Zm.375 0a.375.375 0 1 1-.75 0 .375.375 0 0 1 .75 0Z" />
              </svg>
            </button>

            {/* Brush/Mask Upload Button */}
            <button
              type="button"
              onClick={() => maskBaseInputRef.current?.click()}
              disabled={isLoading}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="Upload Image & Paint Mask"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="m14.622 17.897-10.68-2.913" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M18.376 2.622a1 1 0 1 1 3.002 3.002L17.36 9.643a.5.5 0 0 0 0 .707l.944.944a2.41 2.41 0 0 1 0 3.408l-.944.944a.5.5 0 0 1-.707 0L8.354 7.348a.5.5 0 0 1 0-.707l.944-.944a2.41 2.41 0 0 1 3.408 0l.944.944a.5.5 0 0 0 .707 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 8c-1.804 2.71-3.97 3.46-6.583 3.948a.507.507 0 0 0-.302.819l7.32 8.883a1 1 0 0 0 1.185.204C12.735 20.405 16 16.792 16 15" />
              </svg>
            </button>

            {/* Document Upload Button */}
            <button
              type="button"
              onClick={() => docInputRef.current?.click()}
              disabled={isLoading}
              className="p-2 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer disabled:opacity-50 disabled:cursor-not-allowed"
              title="Upload Document"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 14.25v-2.625a3.375 3.375 0 0 0-3.375-3.375h-1.5A1.125 1.125 0 0 1 13.5 7.125v-1.5a3.375 3.375 0 0 0-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 0 0-9-9Z" />
              </svg>
            </button>
          </div>

          {/* Core Text Input */}
          <textarea
            ref={textareaRef}
            rows={1}
            value={text}
            onChange={handleTextChange}
            onKeyDown={handleKeyDown}
            disabled={isLoading}
            placeholder="Type a message, run a ComfyUI workflow, or upload briefs..."
            className="flex-1 max-h-[200px] resize-none overflow-y-auto py-2.5 px-3 bg-transparent border-0 text-slate-100 text-sm placeholder-slate-500 focus:outline-none focus:ring-0 leading-relaxed font-sans custom-scrollbar"
          />

          {/* Submit Action */}
          {isLoading ? (
            <button
              type="button"
              onClick={handleCancel}
              className="p-2.5 rounded-xl bg-red-600 hover:bg-red-500 text-white shadow-lg shadow-red-600/10 hover:shadow-red-600/20 transition-all cursor-pointer mb-0.5 mr-0.5 flex items-center justify-center"
              title="Cancel Response"
            >
              {/* Stop icon (square) */}
              <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5">
                <rect x="6" y="6" width="12" height="12" rx="1.5" />
              </svg>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSubmit}
              disabled={!text.trim() && !stagedImage && !stagedImage2 && !stagedDocument}
              className="p-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white shadow-lg shadow-indigo-600/10 hover:shadow-indigo-600/20 transition-all cursor-pointer disabled:opacity-30 disabled:hover:bg-indigo-600 disabled:cursor-not-allowed mb-0.5 mr-0.5"
              title="Send message"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor" className="w-5 h-5">
                <path strokeLinecap="round" strokeLinejoin="round" d="M6 12 3.269 3.125A59.769 59.769 0 0 1 21.485 12 59.768 59.768 0 0 1 3.27 20.875L5.999 12Zm0 0h7.5" />
              </svg>
            </button>
          )}
        </div>
      </div>
      <div className="text-center mt-2">
        <span className="text-[10px] text-slate-600 font-semibold tracking-wider uppercase">
          Supported inputs: text, .png, .jpg, .pdf, .docx, .txt
        </span>
      </div>

      {/* Masking Modal */}
      {isMaskModalOpen && maskModalImage && (
        <MaskingModal
          isOpen={isMaskModalOpen}
          imageFile={maskModalImage}
          onClose={() => {
            setIsMaskModalOpen(false);
            setMaskModalImage(null);
          }}
          onSave={handleMaskSave}
        />
      )}
    </div>
  );
};
