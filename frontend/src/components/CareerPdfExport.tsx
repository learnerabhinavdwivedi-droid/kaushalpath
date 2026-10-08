import React, { useState } from 'react';
import jsPDF, { GState } from 'jspdf';
import { RoadmapResult } from '../api/client';
import { Download } from 'lucide-react';

interface CareerPdfExportProps {
  choiceName: string;
  roadmap: RoadmapResult | null;
}

export function buildRoadmapPdf(choiceName: string, roadmap: RoadmapResult): jsPDF {
  const doc = new jsPDF('p', 'mm', 'a4');
  const pageW = doc.internal.pageSize.getWidth();
  const pageH = doc.internal.pageSize.getHeight();
  const margin = 18;
  const contentW = pageW - margin * 2;

  // 1. Soft Vector Brand Accents (Replacing raster JPGs)
  try {
    const gstate = new GState({ opacity: 0.12 });
    doc.setGState(gstate);

    // Lavender flourish top-right
    doc.setFillColor(221, 185, 251); // #DDB9FB
    doc.circle(pageW - 12, 22, 34, 'F');

    // Soft Orange blob bottom-left
    doc.setFillColor(255, 79, 0); // #FF4F00
    doc.circle(12, pageH - 22, 28, 'F');

    // Subtle Green accent card shape bottom-right
    doc.setFillColor(15, 123, 63); // #0F7B3F
    doc.roundedRect(pageW - 45, pageH - 42, 50, 35, 8, 8, 'F');

    // Reset GState to full opacity for text and lines
    doc.setGState(new GState({ opacity: 1.0 }));
  } catch (e) {
    // Graceful fallback if GState is not available
  }

  let y = 20;

  // Header: 28-32pt bold "Kaushal Path" in #1D4ED8 (rgb: 29, 78, 216)
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(28);
  doc.setTextColor(29, 78, 216);
  doc.text('Kaushal Path', margin, y);
  y += 7;

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(10);
  doc.setTextColor(85, 85, 74);
  doc.text('Personalized Career Roadmap & Vocational Guide', margin, y);
  y += 4;

  // Thin rule beneath header
  doc.setDrawColor(29, 78, 216);
  doc.setLineWidth(0.6);
  doc.line(margin, y, pageW - margin, y);
  y += 9;

  // Choice Heading: 20-22pt
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(21);
  doc.setTextColor(10, 10, 10);
  const choiceLines = doc.splitTextToSize(choiceName, contentW);
  doc.text(choiceLines, margin, y);
  y += choiceLines.length * 7.5 + 2;

  // roadmap.expected (if present): italic 11pt quote block with left accent bar
  if (roadmap.expected) {
    const expText = `"${roadmap.expected.trim()}"`;
    doc.setFont('helvetica', 'italic');
    doc.setFontSize(10.5);
    doc.setTextColor(75, 85, 99);
    const expLines = doc.splitTextToSize(expText, contentW - 8);
    const blockH = Math.max(10, expLines.length * 4.8 + 2);

    // Left accent bar in #FF4F00
    doc.setDrawColor(255, 79, 0);
    doc.setLineWidth(1.2);
    doc.line(margin, y, margin, y + blockH);

    doc.text(expLines, margin + 4, y + 4);
    y += blockH + 6;
  } else {
    y += 2;
  }

  // Section title
  doc.setFont('helvetica', 'bold');
  doc.setFontSize(13);
  doc.setTextColor(29, 78, 216);
  doc.text('Step-by-Step Milestones', margin, y);
  y += 6;

  // Timeline auto-shrink scaling
  const steps = roadmap.steps || [];
  const stepsCount = steps.length;
  const isCompact = stepsCount > 5;
  const badgeR = isCompact ? 3.5 : 4.4;
  const titleSize = isCompact ? 10.5 : 12;
  const detailSize = isCompact ? 8.8 : 10;
  const stepGap = isCompact ? 3.8 : 5.8;

  const badgeX = margin + badgeR + 1;
  const textX = badgeX + badgeR + 4;
  const textW = pageW - margin - textX;

  // Connecting vertical timeline bar if multiple steps
  if (stepsCount > 1) {
    doc.setDrawColor(219, 234, 254); // #DBEAFE
    doc.setLineWidth(0.8);
    // Draw vertical connector behind badges
    doc.line(badgeX, y + badgeR, badgeX, y + (stepsCount - 1) * (isCompact ? 22 : 28));
  }

  steps.forEach((s, idx) => {
    const stepNum = s.step || idx + 1;
    const badgeCenterY = y + badgeR;

    // Filled circle badge
    doc.setFillColor(29, 78, 216);
    doc.circle(badgeX, badgeCenterY, badgeR, 'F');

    // Number inside badge
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(isCompact ? 8 : 9.5);
    doc.setTextColor(255, 255, 255);
    doc.text(String(stepNum), badgeX, badgeCenterY + (isCompact ? 1.0 : 1.2), { align: 'center' });

    // Step type label
    doc.setFont('helvetica', 'bold');
    doc.setFontSize(titleSize);
    doc.setTextColor(10, 10, 10);
    const typeLabel = s.type ? s.type.charAt(0).toUpperCase() + s.type.slice(1) : `Step ${stepNum}`;
    doc.text(typeLabel, textX, badgeCenterY);

    // Step detail text
    doc.setFont('helvetica', 'normal');
    doc.setFontSize(detailSize);
    doc.setTextColor(75, 85, 99);
    const detailLines = doc.splitTextToSize(s.detail || '', textW);
    doc.text(detailLines, textX, badgeCenterY + (isCompact ? 4.2 : 5.2));

    const itemHeight = badgeR * 2 + detailLines.length * (isCompact ? 3.6 : 4.4);
    y += Math.max(itemHeight, badgeR * 2 + 5) + stepGap;
  });

  // Footer: fixed at bottom of page
  const footerY = 282;
  doc.setDrawColor(229, 231, 235);
  doc.setLineWidth(0.4);
  doc.line(margin, footerY - 5, pageW - margin, footerY - 5);

  doc.setFont('helvetica', 'normal');
  doc.setFontSize(8.5);
  doc.setTextColor(107, 114, 128);

  const leftParts: string[] = [];
  if (roadmap.district) {
    leftParts.push(`District: ${roadmap.district}`);
  }
  if (roadmap.is_demo) {
    leftParts.push('Demo Roadmap');
  } else if (roadmap.source) {
    leftParts.push(roadmap.source);
  }
  const leftText = leftParts.length > 0 ? leftParts.join(' • ') : 'Vocational Path';
  doc.text(leftText, margin, footerY);

  const rightText = 'Generated by Kaushal Path AI • kaushalpath.in';
  doc.text(rightText, pageW - margin, footerY, { align: 'right' });

  return doc;
}

export async function generateRoadmapPdfBlob(choiceName: string, roadmap: RoadmapResult): Promise<Blob> {
  const doc = buildRoadmapPdf(choiceName, roadmap);
  return doc.output('blob');
}

export const CareerPdfExport: React.FC<CareerPdfExportProps> = ({ choiceName, roadmap }) => {
  const [exporting, setExporting] = useState(false);

  const handleDownload = () => {
    if (!roadmap) return;
    setExporting(true);
    try {
      const doc = buildRoadmapPdf(choiceName, roadmap);
      const filename = `KaushalPath_Roadmap_${choiceName.replace(/\s+/g, '_')}.pdf`;
      doc.save(filename);
    } catch (e) {
      console.error(e);
      alert('Failed to generate PDF');
    } finally {
      setExporting(false);
    }
  };

  return (
    <button
      onClick={handleDownload}
      disabled={exporting || !roadmap}
      className="btn-secondary flex items-center gap-2"
    >
      <Download size={18} /> {exporting ? 'Generating PDF...' : 'Download PDF'}
    </button>
  );
};
