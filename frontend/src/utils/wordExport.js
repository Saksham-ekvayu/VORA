import {
  Document,
  Packer,
  Paragraph,
  TextRun,
  HeadingLevel,
  AlignmentType,
} from "docx";
import { saveAs } from "file-saver";

export async function exportCustomFrameworkToWord(
  frameworkName,
  groupedControls,
  totalCount
) {
  const doc = new Document({
    sections: [
      {
        properties: {},
        children: [
          // Title Page
          new Paragraph({
            text: frameworkName || "Custom Compliance Framework",
            heading: HeadingLevel.TITLE,
            alignment: AlignmentType.CENTER,
            spacing: { after: 400 },
          }),
          new Paragraph({
            text: `Created: ${new Date().toLocaleDateString("en-US", {
              year: "numeric",
              month: "long",
              day: "numeric",
            })}`,
            alignment: AlignmentType.CENTER,
            spacing: { after: 800 },
          }),

          // Summary Section
          new Paragraph({
            text: "Framework Summary",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 200 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: "Total Controls: ", bold: true }),
              new TextRun({ text: totalCount.toString() }),
            ],
            spacing: { after: 100 },
          }),
          new Paragraph({
            children: [
              new TextRun({ text: "Source Frameworks: ", bold: true }),
              new TextRun({
                text: Object.keys(groupedControls).length.toString(),
              }),
            ],
            spacing: { after: 200 },
          }),

          // Breakdown by Framework
          new Paragraph({
            text: "Controls Breakdown by Framework",
            heading: HeadingLevel.HEADING_2,
            spacing: { before: 200, after: 200 },
          }),
          ...Object.entries(groupedControls).map(
            ([, { framework, controls }]) =>
              new Paragraph({
                children: [
                  new TextRun({ text: `• ${framework.name}: `, bold: true }),
                  new TextRun({ text: `${controls.length} controls` }),
                ],
                spacing: { after: 100 },
              })
          ),

          // Page break before controls
          new Paragraph({
            text: "",
            pageBreakBefore: true,
          }),

          // Controls Section
          new Paragraph({
            text: "Framework Controls",
            heading: HeadingLevel.HEADING_1,
            spacing: { before: 400, after: 300 },
          }),

          // Generate controls grouped by framework
          ...generateControlsSections(groupedControls),
        ],
      },
    ],
  });

  // Generate and download the document
  const blob = await Packer.toBlob(doc);
  const fileName = `${frameworkName || "Custom_Framework"}_${new Date().toISOString().split("T")[0]}.docx`;
  saveAs(blob, fileName);
}

function generateControlsSections(groupedControls) {
  const sections = [];

  Object.entries(groupedControls).forEach(([, { framework, controls }]) => {
    // Framework heading
    sections.push(
      new Paragraph({
        text: `From ${framework.name}`,
        heading: HeadingLevel.HEADING_2,
        spacing: { before: 400, after: 200 },
      })
    );

    // Group controls by category
    const controlsByCategory = {};
    controls.forEach((control) => {
      if (!controlsByCategory[control.category]) {
        controlsByCategory[control.category] = [];
      }
      controlsByCategory[control.category].push(control);
    });

    // Generate controls by category
    Object.entries(controlsByCategory).forEach(
      ([category, categoryControls]) => {
        sections.push(
          new Paragraph({
            text: category,
            heading: HeadingLevel.HEADING_3,
            spacing: { before: 300, after: 150 },
          })
        );

        // Add each control
        categoryControls.forEach((control, index) => {
          sections.push(
            new Paragraph({
              children: [
                new TextRun({
                  text: `${control.id}: `,
                  bold: true,
                  color: "2D7EF7",
                }),
                new TextRun({ text: control.title, bold: true }),
              ],
              spacing: { before: 200, after: 100 },
            }),
            new Paragraph({
              children: [
                new TextRun({ text: "Type: ", bold: true }),
                new TextRun({ text: control.type }),
              ],
              spacing: { after: 100 },
            }),
            new Paragraph({
              children: [
                new TextRun({ text: "Description: ", bold: true }),
                new TextRun({ text: control.description }),
              ],
              spacing: {
                after: index < categoryControls.length - 1 ? 200 : 300,
              },
            })
          );
        });
      }
    );
  });

  return sections;
}
