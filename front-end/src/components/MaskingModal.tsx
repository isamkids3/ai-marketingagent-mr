import React, { useEffect, useRef, useState } from "react";

interface MaskingModalProps {
  isOpen: boolean;
  imageFile: File;
  onClose: () => void;
  onSave: (maskBlob: Blob) => void;
}

export const MaskingModal: React.FC<MaskingModalProps> = ({
  isOpen,
  imageFile,
  onClose,
  onSave,
}) => {
  const [brushSize, setBrushSize] = useState<number>(30);
  const [brushMode, setBrushMode] = useState<"draw" | "erase">("draw");
  const [imageSrc, setImageSrc] = useState<string | null>(null);
  
  const containerRef = useRef<HTMLDivElement>(null);
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const imageRef = useRef<HTMLImageElement>(null);
  
  const isDrawingRef = useRef<boolean>(false);
  const lastPosRef = useRef<{ x: number; y: number } | null>(null);
  const undoStackRef = useRef<ImageData[]>([]);

  // Load image preview source
  useEffect(() => {
    if (!isOpen) return;
    const reader = new FileReader();
    reader.onload = (e) => {
      setImageSrc(e.target?.result as string);
    };
    reader.readAsDataURL(imageFile);
  }, [isOpen, imageFile]);

  // Adjust canvas size to match image dimensions once loaded
  const handleImageLoad = () => {
    const img = imageRef.current;
    const canvas = canvasRef.current;
    if (!img || !canvas) return;

    canvas.width = img.naturalWidth || img.width || 800;
    canvas.height = img.naturalHeight || img.height || 600;

    const ctx = canvas.getContext("2d");
    if (ctx) {
      ctx.clearRect(0, 0, canvas.width, canvas.height);
      ctx.fillStyle = "rgba(0, 0, 0, 0)";
      ctx.fillRect(0, 0, canvas.width, canvas.height);
      
      // Save initial blank state to undo stack
      undoStackRef.current = [ctx.getImageData(0, 0, canvas.width, canvas.height)];
    }
  };

  // Manually trigger handleImageLoad if image is already complete (cached)
  useEffect(() => {
    const img = imageRef.current;
    if (img) {
      if (img.complete) {
        handleImageLoad();
      } else {
        img.onload = handleImageLoad;
      }
    }
  }, [imageSrc]);

  // Drawing event helpers
  const getCanvasCoords = (e: any) => {
    const canvas = canvasRef.current;
    if (!canvas) return null;

    const rect = canvas.getBoundingClientRect();
    let clientX = 0;
    let clientY = 0;

    // Safely check for touches property in case of simulated/emulated touch environments
    if (e.touches && e.touches.length > 0) {
      clientX = e.touches[0].clientX;
      clientY = e.touches[0].clientY;
    } else if (e.changedTouches && e.changedTouches.length > 0) {
      clientX = e.changedTouches[0].clientX;
      clientY = e.changedTouches[0].clientY;
    } else {
      clientX = e.clientX;
      clientY = e.clientY;
    }

    // Convert screen coordinates to canvas source coordinates
    const rectWidth = rect.width || 1;
    const rectHeight = rect.height || 1;
    const scaleX = canvas.width / rectWidth;
    const scaleY = canvas.height / rectHeight;

    return {
      x: (clientX - rect.left) * scaleX,
      y: (clientY - rect.top) * scaleY,
    };
  };

  const startDrawing = (e: any) => {
    // Only allow left mouse button (0)
    if (e.button !== undefined && e.button !== 0) return;

    isDrawingRef.current = true;
    const coords = getCanvasCoords(e);
    if (coords) {
      lastPosRef.current = coords;
      
      // Draw a single dot on click/tap
      const canvas = canvasRef.current;
      const ctx = canvas?.getContext("2d");
      if (canvas && ctx) {
        ctx.beginPath();
        if (brushMode === "draw") {
          ctx.globalCompositeOperation = "source-over";
          ctx.fillStyle = "rgba(239, 68, 68, 0.75)";
        } else {
          ctx.globalCompositeOperation = "destination-out";
          ctx.fillStyle = "rgba(0, 0, 0, 1.0)";
        }
        const rectWidth = canvas.getBoundingClientRect().width || 1;
        const scale = canvas.width / rectWidth;
        ctx.arc(coords.x, coords.y, (brushSize / 2) * scale, 0, Math.PI * 2);
        ctx.fill();
      }
    }
  };

  const draw = (e: any) => {
    if (!isDrawingRef.current) return;

    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    const coords = getCanvasCoords(e);

    if (!canvas || !ctx || !coords || !lastPosRef.current) return;

    ctx.beginPath();
    ctx.moveTo(lastPosRef.current.x, lastPosRef.current.y);
    ctx.lineTo(coords.x, coords.y);
    
    // Inpaint mask uses red indicator for visibility
    if (brushMode === "draw") {
      ctx.globalCompositeOperation = "source-over";
      ctx.strokeStyle = "rgba(239, 68, 68, 0.75)";
      ctx.fillStyle = "rgba(239, 68, 68, 0.75)";
    } else {
      ctx.globalCompositeOperation = "destination-out";
      ctx.strokeStyle = "rgba(0, 0, 0, 1.0)";
      ctx.fillStyle = "rgba(0, 0, 0, 1.0)";
    }

    const rectWidth = canvas.getBoundingClientRect().width || 1;
    ctx.lineWidth = brushSize * (canvas.width / rectWidth);
    ctx.lineCap = "round";
    ctx.lineJoin = "round";
    ctx.stroke();

    lastPosRef.current = coords;
  };

  const stopDrawing = () => {
    if (!isDrawingRef.current) return;
    isDrawingRef.current = false;
    lastPosRef.current = null;

    // Save state to undo stack
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (canvas && ctx) {
      if (undoStackRef.current.length >= 20) {
        undoStackRef.current.shift();
      }
      undoStackRef.current.push(ctx.getImageData(0, 0, canvas.width, canvas.height));
    }
  };

  // Setup global mouse up events to handle release outside canvas
  useEffect(() => {
    const handleGlobalMouseUp = () => {
      stopDrawing();
    };
    window.addEventListener("mouseup", handleGlobalMouseUp);
    window.addEventListener("touchend", handleGlobalMouseUp);
    return () => {
      window.removeEventListener("mouseup", handleGlobalMouseUp);
      window.removeEventListener("touchend", handleGlobalMouseUp);
    };
  }, []);

  const handleUndo = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx || undoStackRef.current.length <= 1) return;

    // Pop the current state and restore the previous one
    undoStackRef.current.pop();
    const prevState = undoStackRef.current[undoStackRef.current.length - 1];
    ctx.putImageData(prevState, 0, 0);
  };

  const handleClear = () => {
    const canvas = canvasRef.current;
    const ctx = canvas?.getContext("2d");
    if (!canvas || !ctx) return;

    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.fillStyle = "rgba(0, 0, 0, 0)";
    ctx.fillRect(0, 0, canvas.width, canvas.height);

    undoStackRef.current = [ctx.getImageData(0, 0, canvas.width, canvas.height)];
  };

  const handleSave = () => {
    const canvas = canvasRef.current;
    if (!canvas) return;

    // Create an offscreen canvas to generate a clean black and white mask
    const maskCanvas = document.createElement("canvas");
    maskCanvas.width = canvas.width;
    maskCanvas.height = canvas.height;
    
    const mCtx = maskCanvas.getContext("2d");
    const srcCtx = canvas.getContext("2d");
    
    if (!mCtx || !srcCtx) return;

    // Read drawn pixels from the source canvas
    const imgData = srcCtx.getImageData(0, 0, canvas.width, canvas.height);
    const pixels = imgData.data;
    
    // Create new blank image data for the black and white mask
    const maskImgData = mCtx.createImageData(canvas.width, canvas.height);
    const maskPixels = maskImgData.data;

    for (let i = 0; i < pixels.length; i += 4) {
      const alpha = pixels[i + 3];
      if (alpha > 10) {
        // Painted region -> White (255, 255, 255, 255)
        maskPixels[i] = 255;
        maskPixels[i + 1] = 255;
        maskPixels[i + 2] = 255;
        maskPixels[i + 3] = 255;
      } else {
        // Unpainted region -> Black (0, 0, 0, 255)
        maskPixels[i] = 0;
        maskPixels[i + 1] = 0;
        maskPixels[i + 2] = 0;
        maskPixels[i + 3] = 255;
      }
    }

    mCtx.putImageData(maskImgData, 0, 0);

    // Export as PNG Blob
    maskCanvas.toBlob((blob) => {
      if (blob) {
        onSave(blob);
      }
    }, "image/png");
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-slate-950/80 backdrop-blur-md p-4 animate-fade-in">
      <div className="flex flex-col bg-slate-900 border border-slate-800 rounded-2xl w-full max-w-5xl h-[85vh] shadow-[0_20px_50px_rgba(0,0,0,0.5)] overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-950/30">
          <div>
            <h3 className="text-base font-bold text-white tracking-wide">Image Masking Tool</h3>
            <p className="text-xs text-slate-400 mt-0.5">Paint over the areas you want the AI to replace or edit</p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer"
          >
            <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-5 h-5">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18 18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Workspace Canvas Area */}
        <div 
          ref={containerRef}
          className="flex-1 overflow-auto bg-slate-950/40 flex items-center justify-center p-8 relative custom-scrollbar select-none"
        >
          {imageSrc && (
            <div className="relative shadow-2xl border border-slate-800/50 rounded-lg overflow-hidden max-w-full max-h-[50vh]">
              {/* Underlying original image */}
              <img
                ref={imageRef}
                src={imageSrc}
                alt="Base for masking"
                onLoad={handleImageLoad}
                className="block object-contain max-w-full max-h-[50vh] pointer-events-none select-none"
              />
              
              {/* Absolute overlay canvas for drawing the mask */}
              <canvas
                ref={canvasRef}
                onMouseDown={startDrawing}
                onMouseMove={draw}
                onTouchStart={startDrawing}
                onTouchMove={draw}
                className="absolute inset-0 w-full h-full cursor-crosshair touch-none"
              />
            </div>
          )}
        </div>

        {/* Toolbar & Controls */}
        <div className="px-6 py-4 border-t border-slate-800 bg-slate-950/50 flex flex-wrap items-center justify-between gap-4">
          <div className="flex items-center gap-6">
            {/* Mode selection */}
            <div className="flex items-center bg-slate-900 border border-slate-800 p-1 rounded-lg">
              <button
                type="button"
                onClick={() => setBrushMode("draw")}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  brushMode === "draw"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                </svg>
                Brush
              </button>
              <button
                type="button"
                onClick={() => setBrushMode("erase")}
                className={`px-3 py-1.5 rounded-md text-xs font-semibold flex items-center gap-1.5 transition-all cursor-pointer ${
                  brushMode === "erase"
                    ? "bg-indigo-600 text-white shadow"
                    : "text-slate-400 hover:text-slate-200"
                }`}
              >
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-3.5 h-3.5">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M9.75 9.75l4.5 4.5m0-4.5l-4.5 4.5M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
                </svg>
                Eraser
              </button>
            </div>

            {/* Brush size slider */}
            <div className="flex items-center gap-3">
              <span className="text-xs text-slate-400 font-semibold select-none">Size: {brushSize}px</span>
              <input
                type="range"
                min="5"
                max="100"
                value={brushSize}
                onChange={(e) => setBrushSize(parseInt(e.target.value))}
                className="w-32 h-1 bg-slate-800 rounded-lg appearance-none cursor-pointer accent-indigo-500"
              />
            </div>
          </div>

          <div className="flex items-center gap-2">
            {/* Action controls */}
            <button
              type="button"
              onClick={handleUndo}
              disabled={undoStackRef.current.length <= 1}
              className="p-2 rounded-lg border border-slate-850 bg-slate-900/60 text-slate-300 hover:text-white hover:bg-slate-800/80 transition-all cursor-pointer disabled:opacity-40 disabled:cursor-not-allowed"
              title="Undo last stroke"
            >
              <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor" className="w-4 h-4">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
              </svg>
            </button>
            <button
              type="button"
              onClick={handleClear}
              className="px-3 py-2 rounded-lg border border-slate-850 bg-slate-900/60 text-slate-300 hover:text-white hover:bg-slate-800/80 text-xs font-semibold transition-all cursor-pointer"
            >
              Clear Mask
            </button>
            <div className="w-px h-5 bg-slate-800 mx-1"></div>
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 rounded-lg bg-slate-900 border border-slate-800 text-slate-300 hover:text-white transition-all text-xs font-semibold cursor-pointer"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              className="px-4 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 text-white font-semibold text-xs shadow-md shadow-indigo-600/15 hover:shadow-indigo-600/30 transition-all cursor-pointer"
            >
              Apply Mask
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
