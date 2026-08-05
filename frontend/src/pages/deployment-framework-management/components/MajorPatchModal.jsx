/* eslint-disable react/prop-types */

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Icon from "@/components/custom/Icon";
import FileTypeCard from "@/components/custom/FileTypeCard";
import { Input } from "@/components/ui/input";
import { useState, useRef } from "react";
import { useModalState } from "@/hooks/useModalState";
import {
  createDocumentFromFile,
  submitPatch,
  getNextVersion,
} from "./helper/patchModalHelpers";
import { normalizeFileType } from "./helper/normalizeFileType";

function MajorPatchModal({ isOpen, onClose, framework, onSuccess }) {
  const [documents, setDocuments] = useState([]);
  const { loading: isLoading, setLoading: setIsLoading } = useModalState();
  const fileInputRef = useRef(null);
  const documentsListRef = useRef(null);

  // Clear new files when modal closes
  const handleClose = () => {
    setDocuments([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };
  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);
    const newDocuments = files.map((file, index) =>
      createDocumentFromFile(file, index)
    );

    setDocuments((prev) => [...newDocuments, ...prev]);

    setTimeout(() => {
      documentsListRef.current?.scrollTo({
        top: 0,
        behavior: "smooth",
      });
    }, 0);

    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleReplaceDocument = (docId) => {
    fileInputRef.current?.click();
    // Store the document ID to replace
    fileInputRef.current.dataset.replaceId = docId;
  };

  const handleFileReplace = (event) => {
    const files = Array.from(event.target.files);
    const replaceId = event.target.dataset.replaceId;

    if (files.length > 0 && replaceId) {
      const file = files[0];
      setDocuments((prev) =>
        prev.map((doc) =>
          doc.id === replaceId
            ? {
                ...doc,
                name: file.name,
                size: file.size,
                type: normalizeFileType(file.type, file.name),
                file: file,
              }
            : doc
        )
      );
    }

    // Clear the replace ID and reset input
    delete event.target.dataset.replaceId;
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
  };

  const handleFileInputChange = (event) => {
    if (event.target.dataset.replaceId) {
      handleFileReplace(event);
    } else {
      handleFileUpload(event);
    }
  };

  const handleRemoveDocument = (docId) => {
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
  };

  const getDocumentCountText = () => {
    if (!documents || documents.length === 0) {
      return "no documents yet";
    }
    const count = documents.length;
    const plural = count === 1 ? "" : "s";
    return `${count} document${plural} in this patch`;
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      await submitPatch(framework, documents, "major", onSuccess, onClose);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-3xl lg:max-h-[80vh] overflow-y-auto">
        <ModalHeader
          icon="rocket"
          title="Create Major Patch"
          description="Upload a new document set."
        />

        {/* Replication Banner */}
        <div className="border-b border-border p-2 mb-3 bg-primary/10 flex items-center gap-2">
          <div className="bg-primary/10 rounded p-2 flex items-center justify-center">
            <Icon name="rocket" size={20} className="text-amber-500" />
          </div>
          <div className="flex flex-col justify-start items-start gap-1">
            <span className="font-semibold text-sm text-justify">
              Fresh document set — nothing inherited
            </span>
            <p className="text-xs text-muted-foreground text-justify">
              A major version is a structural reset. No prior documents are
              carried over. Upload a completely new set for fresh control
              extraction and gap analysis.
            </p>
          </div>
        </div>

        {/* Documents Section */}
        <div className="mb-2 p-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-semibold text-foreground uppercase">
              {getDocumentCountText()}
            </h3>
            <Badge variant="blue" className="text-xs">
              Fresh Start
            </Badge>
          </div>

          {/* Documents List */}
          <div
            ref={documentsListRef}
            className="space-y-1 max-h-52 overflow-y-auto"
          >
            {documents && documents.length > 0 ? (
              documents.map((doc) => (
                <div
                  key={doc.id}
                  className="flex items-center justify-between p-2 border border-border rounded bg-card"
                >
                  <div className="flex items-center gap-3 flex-1 w-80">
                    <FileTypeCard
                      fileName={doc.name}
                      fileSize={doc.size}
                      fileType={doc.type}
                      size="sm"
                    />
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <Button
                      variant="default"
                      size="xs"
                      className="text-xs"
                      onClick={() => handleReplaceDocument(doc.id)}
                    >
                      <Icon name="refresh" size={11} /> Replace
                    </Button>
                    <Button
                      variant="destructive"
                      size="xs"
                      className="text-xs"
                      onClick={() => handleRemoveDocument(doc.id)}
                    >
                      <Icon name="trash" size={11} /> Remove
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-muted-foreground text-sm py-8">
                <Icon
                  name="open-folder"
                  size={32}
                  className="mx-auto mb-2 opacity-50 text-amber-500"
                />
                <p>No documents uploaded yet</p>
              </div>
            )}
          </div>

          {/* Hidden File Input */}
          <Input
            ref={fileInputRef}
            type="file"
            multiple
            onChange={handleFileInputChange}
            className="hidden"
            accept=".pdf,.doc,.docx"
          />

          {/* Add Document Button */}
          <Button
            variant="outline"
            className="w-full mt-3 text-sm"
            onClick={() => fileInputRef.current?.click()}
          >
            <Icon name="plus" size={14} /> Add document
          </Button>
        </div>

        {/* Replication Banner */}
        <div className="border border-border rounded p-2 mb-2 flex items-center gap-2 mx-2">
          <p className="text-xs text-muted-foreground text-justify">
            🚀 No documents are inherited from v1.0.2. Add as many new documents
            as needed — you can also upload after the version is created.
          </p>
        </div>

        {/* Footer */}
        <ModalFooter
          onCancel={handleClose}
          onSubmit={handleSubmit}
          isSaving={isLoading}
          isActionDisabled={documents.length === 0}
          actionLabel={`Create Major Patch ${getNextVersion(framework.currentPackageVersion, "major")}`}
          savingLabel="Creating..."
          actionIcon="rocket"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
}

export default MajorPatchModal;
