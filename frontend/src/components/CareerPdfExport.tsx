import React, { useRef, useState } from 'react';
import html2canvas from 'html2canvas';
import jsPDF from 'jspdf';
import { RoadmapResult } from '../api/client';
import { Download } from 'lucide-react';

interface CareerPdfExportProps {
  choiceName: string;
  roadmap: RoadmapResult | null;
}

export const CareerPdfExport: React.FC<CareerPdfExportProps> = ({ choiceName, roadmap }) => {
  const [exporting, setExporting] = useState(false);
  const pdfRef = useRef<HTMLDivElement>(null);

  const generatePDF = async () => {
    if (!pdfRef.current || !roadmap) return;
    setExporting(true);
    try {
      const canvas = await html2canvas(pdfRef.current, { scale: 2, useCORS: true });
      const imgData = canvas.toDataURL('image/png');
      const pdf = new jsPDF('p', 'mm', 'a4');
      const pdfWidth = pdf.internal.pageSize.getWidth();
      const pdfHeight = (canvas.height * pdfWidth) / canvas.width;
      pdf.addImage(imgData, 'PNG', 0, 0, pdfWidth, pdfHeight);
      pdf.save(`KaushalPath_Roadmap_${choiceName.replace(/\s+/g, '_')}.pdf`);
    } catch (e) {
      console.error(e);
      alert('Failed to generate PDF');
    } finally {
      setExporting(false);
    }
  };

  return (
    <>
      <button onClick={generatePDF} disabled={exporting || !roadmap} className="btn-secondary flex items-center gap-2">
        <Download size={18} /> {exporting ? 'Generating PDF...' : 'Download PDF'}
      </button>

      {/* Hidden container for PDF Generation */}
      {roadmap && (
        <div className="overflow-hidden h-0 w-0 absolute opacity-0 pointer-events-none">
          <div ref={pdfRef} className="bg-page p-10 w-[800px] text-ink relative font-sans" style={{ minHeight: '1120px' }}>
            {/* Background elements */}
            <div className="absolute top-0 right-0 w-[400px] h-[400px] bg-lavender/30 rounded-full mix-blend-multiply blur-[80px]"></div>
            <div className="absolute bottom-0 left-0 w-[400px] h-[400px] bg-orange/20 rounded-full mix-blend-multiply blur-[80px]"></div>
            
            {/* Using the AI doodles for decoration */}
            <img src="/doodles/doodle_success.jpg" alt="" className="absolute top-10 right-10 w-40 h-40 opacity-80 mix-blend-multiply object-contain" crossOrigin="anonymous" />
            <img src="/doodles/doodle_puzzle.jpg" alt="" className="absolute bottom-10 left-10 w-40 h-40 opacity-80 mix-blend-multiply object-contain" crossOrigin="anonymous" />
            
            <div className="relative z-10">
              <div className="border-b-4 border-accent pb-4 mb-8">
                <h1 className="text-4xl font-extrabold text-accent mb-2">Kaushal Path</h1>
                <p className="text-xl text-textSecondary">Your Personalized Career Roadmap</p>
              </div>

              <h2 className="text-5xl font-bold text-ink mb-6 leading-tight">{choiceName}</h2>
              {roadmap.expected && (
                <p className="text-2xl text-textSecondary italic mb-10 border-l-4 border-orange pl-6 py-2 bg-orange/5 rounded-r-xl">
                  "{roadmap.expected}"
                </p>
              )}

              <div className="bg-white rounded-2xl shadow-sm border-2 border-accent/10 p-8">
                <h3 className="text-2xl font-bold text-accent mb-6">Step-by-Step Guide</h3>
                <div className="space-y-8">
                  {roadmap.steps.map((s, idx) => (
                    <div key={idx} className="flex gap-6">
                      <div className="flex-shrink-0 w-14 h-14 rounded-full bg-accent text-white flex items-center justify-center text-2xl font-bold shadow-md">
                        {idx + 1}
                      </div>
                      <div>
                        <h4 className="text-2xl font-bold capitalize mb-2">{s.type}</h4>
                        <p className="text-xl text-textSecondary leading-relaxed">{s.detail}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
              
              <div className="mt-16 text-center text-gray-400 font-mono text-sm border-t border-gray-200 pt-8">
                Generated securely by Kaushal Path AI • www.kaushalpath.in
              </div>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
