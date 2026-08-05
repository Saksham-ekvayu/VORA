/* eslint-disable react/prop-types */

import { Dialog, DialogContent } from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import Icon from "@/components/custom/Icon";
import { ModalFooter, ModalHeader } from "@/components/custom/modal";

import FileTypeCard from "@/components/custom/FileTypeCard";
import { useState, useRef } from "react";
import { useModalState } from "@/hooks/useModalState";
import { Input } from "@/components/ui/input";
import {
  createReplicatedDocument,
  createDocumentFromFile,
  submitPatch,
  getNextVersion,
} from "./helper/patchModalHelpers";
import { normalizeFileType } from "./helper/normalizeFileType";

const mergeUploadedFilesIntoDocuments = (documents, files) => {
  const nextDocuments = [...documents];

  files.forEach((file, index) => {
    const existingIndex = nextDocuments.findIndex(
      (doc) => doc.name === file.name
    );

    if (existingIndex === -1) {
      nextDocuments.unshift(createDocumentFromFile(file, index));
      return;
    }

    const existingDoc = nextDocuments[existingIndex];
    nextDocuments[existingIndex] = {
      ...existingDoc,
      fileId: existingDoc.fileId || existingDoc.id,
      size: file.size,
      type: normalizeFileType(file.type, file.name),
      aiExtraction: null,
      file,
      replicated: false,
      action: "replace",
    };
  });

  return nextDocuments;
};

const MinorPatchModal = ({
  isOpen,
  onClose,
  documents: initialDocuments = [],
  framework,
  onSuccess,
}) => {
  // Transform initial documents into patch entries.
  // Existing package docs should be replicated by default in a minor patch.
  const transformedInitialDocuments = initialDocuments.map(
    createReplicatedDocument
  );

  const [documents, setDocuments] = useState(transformedInitialDocuments);
  const [removedDocuments, setRemovedDocuments] = useState([]);
  const { loading: isLoading, setLoading: setIsLoading } = useModalState();
  const fileInputRef = useRef(null);
  const documentsListRef = useRef(null);

  // Clear new files when modal closes
  const handleClose = () => {
    setDocuments(transformedInitialDocuments);
    setRemovedDocuments([]);
    if (fileInputRef.current) {
      fileInputRef.current.value = "";
    }
    onClose();
  };

  const handleFileUpload = (event) => {
    const files = Array.from(event.target.files);

    setDocuments((prev) => mergeUploadedFilesIntoDocuments(prev, files));

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

  const handleRemoveDocument = (docId) => {
    const removed = documents.find((doc) => doc.id === docId);
    if (removed?.original && removed.fileId) {
      setRemovedDocuments((prev) => [...prev, removed]);
    }
    setDocuments((prev) => prev.filter((doc) => doc.id !== docId));
  };

  const getDocumentCountText = () => {
    const count = documents.length;
    const plural = count === 1 ? "" : "S";
    return `${count} DOCUMENT${plural} IN THIS PATCH`;
  };

  const getInitialDocumentCount = () => {
    return transformedInitialDocuments.length;
  };

  const getDialogDescription = () => {
    const count = getInitialDocumentCount();
    return `Replicate all ${count} document${count === 1 ? "" : "s"} into ${getNextVersion(framework.currentPackageVersion, "minor")} - replace only what changed.`;
  };

  const handleSubmit = async () => {
    setIsLoading(true);
    try {
      await submitPatch(
        framework,
        documents,
        "minor",
        onSuccess,
        handleClose,
        removedDocuments
      );
    } finally {
      setIsLoading(false);
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
        prev.map((doc) => {
          if (doc.id !== replaceId) {
            return doc;
          }

          return {
            ...doc,
            id: replaceId,
            fileId: doc.fileId || replaceId,
            name: file.name,
            size: file.size,
            type: normalizeFileType(file.type, file.name),
            fileVersion: doc.fileVersion,
            aiExtraction: null,
            file: file,
            replicated: false, // Mark as not replicated since it's replaced
            action: "replace",
          };
        })
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

  const replicatedCount = documents.filter((doc) => doc.replicated).length;
  const newCount = documents.filter((doc) => !doc.replicated).length;
  return (
    <Dialog open={isOpen} onOpenChange={handleClose}>
      <DialogContent className="lg:max-w-3xl lg:max-h-[80vh] overflow-y-auto">
        <ModalHeader
          icon="git"
          title="Create Minor Patch"
          description={getDialogDescription()}
        />

        {/* Documents Section */}
        <div className="mb-2 p-2">
          <div className="flex items-center justify-between mb-4">
            <h3 className="text-xs font-semibold text-foreground">
              {getDocumentCountText()}
            </h3>
            <Badge variant="blue" className="text-xs">
              {replicatedCount} replicated • {newCount} new
            </Badge>
          </div>

          {/* Documents List */}
          <div
            ref={documentsListRef}
            className="space-y-1 max-h-72 overflow-y-auto"
          >
            {documents.length > 0 ? (
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
                    <div className="flex items-center gap-1">
                      <Badge variant="secondary" className="text-xs shrink-0">
                        v{doc.fileVersion}
                      </Badge>
                      {doc.replicated && (
                        <Badge variant="green" className="text-xs shrink-0">
                          <Icon name="check" size={10} /> Replicated
                        </Badge>
                      )}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-2">
                    <Button
                      variant="destructive"
                      size="xs"
                      className="text-xs"
                      onClick={() => handleRemoveDocument(doc.id)}
                    >
                      <Icon name="trash" size={11} /> Remove
                    </Button>
                    <Button
                      variant="default"
                      size="xs"
                      className="text-xs"
                      onClick={() => handleReplaceDocument(doc.id)}
                    >
                      <Icon name="refresh" size={11} /> Replace
                    </Button>
                  </div>
                </div>
              ))
            ) : (
              <div className="text-center text-muted-foreground text-sm py-8">
                <Icon
                  name="file-text"
                  size={32}
                  className="mx-auto mb-2 opacity-50"
                />
                <p>No documents in this patch</p>
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
            className="w-full mt-1 text-sm rounded"
            onClick={() => fileInputRef.current?.click()}
          >
            <Icon name="plus" size={14} /> Add document
          </Button>
        </div>

        {/* Replication Banner */}
        <div className="border border-border rounded p-2 mb-2 flex items-center gap-2 mx-2">
          <p className="text-xs text-muted-foreground text-justify">
            📌 Replicated documents carry their current version and AI
            extraction status. Click <strong>Replace</strong> on any row to swap
            in an updated file (resets version and AI status). Click{" "}
            <strong>Add document</strong> below to include new ones in this
            patch — there's no limit.
          </p>
        </div>

        {/* Footer */}
        <ModalFooter
          onCancel={handleClose}
          onSubmit={handleSubmit}
          isSaving={isLoading}
          isActionDisabled={documents.length === 0}
          actionLabel={`Create Minor Patch ${getNextVersion(framework.currentPackageVersion, "minor")}`}
          savingLabel="Creating..."
          actionIcon="git"
          actionType="button"
        />
      </DialogContent>
    </Dialog>
  );
};

export default MinorPatchModal;
