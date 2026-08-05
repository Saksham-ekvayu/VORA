/* eslint-disable react/prop-types */

import { useRef, useState } from "react";
import { cn } from "@/lib/utils";
import { uploadAvatar, resolveAvatarUrl } from "@/services/userService";
import { toast } from "sonner";
import {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogTitle,
} from "@/components/ui/dialog";

const MAX_FILE_SIZE = 5 * 1024 * 1024;
const ALLOWED_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"];

function getInitials(name) {
  if (!name) return "?";
  return name
    .split(" ")
    .filter(Boolean)
    .map((n) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();
}

const getAvatarSizeClasses = (size) => {
  const sizes = {
    xs: "h-6 w-6",
    sm: "h-7 w-7",
    md: "h-8 w-8",
    lg: "h-10 w-10",
    xl: "h-12 w-12",
    "2xl": "h-16 w-16",
    "3xl": "h-20 w-20",
    "4xl": "h-24 w-24",
  };

  if (!size) return sizes.md;
  return sizes[size] || size;
};

const EyeIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-3.5 w-3.5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8z" />
    <circle cx="12" cy="12" r="3" />
  </svg>
);

const CloseIcon = () => (
  <svg
    xmlns="http://www.w3.org/2000/svg"
    className="h-5 w-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
  >
    <path d="M18 6 6 18M6 6l12 12" />
  </svg>
);

/**
 * UserAvatar
 * Props:
 *   user       – { name, avatar }
 *   size       – tailwind size classes (default "h-8 w-8")
 *   className  – extra classes
 *   editable   – show camera overlay + file picker + eye preview button
 *   onUploaded – (rawPath) => void
 */
const UserAvatar = ({
  user,
  size = "md",
  className,
  editable = false,
  disablePreview = false,
  onUploaded,
  uploadFn, // optional – overrides the default uploadAvatar
}) => {
  const avatarSize = getAvatarSizeClasses(size);
  const inputRef = useRef(null);
  const [preview, setPreview] = useState(null);
  const [uploading, setUploading] = useState(false);
  const [lightbox, setLightbox] = useState(false);

  const avatarSrc = preview || resolveAvatarUrl(user?.avatar);
  const isPreviewTrigger = !editable && !disablePreview && avatarSrc;
  const AvatarTrigger = isPreviewTrigger ? "button" : "div";

  const handleFileChange = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    e.target.value = "";

    if (!ALLOWED_TYPES.includes(file.type))
      return toast.error("Only JPG, PNG, WebP or GIF images are allowed.");
    if (file.size > MAX_FILE_SIZE)
      return toast.error("Image must be smaller than 5 MB.");

    const previewUrl = URL.createObjectURL(file);
    setPreview(previewUrl);
    setUploading(true);

    try {
      const doUpload = uploadFn ?? uploadAvatar;
      const response = await doUpload(file);
      const newUrl = response?.data?.avatar || response?.data?.user?.avatar;
      URL.revokeObjectURL(previewUrl);
      if (newUrl) {
        setPreview(resolveAvatarUrl(newUrl));
        onUploaded?.(newUrl);
      }
      toast.success("Avatar updated.");
    } catch (err) {
      setPreview(null);
      URL.revokeObjectURL(previewUrl);
      toast.error(err?.message || "Failed to upload avatar.");
    } finally {
      setUploading(false);
    }
  };

  return (
    <>
      <AvatarTrigger
        type={isPreviewTrigger ? "button" : undefined}
        className={cn(
          avatarSize,
          "relative flex items-center justify-center rounded border border-background shrink-0 overflow-hidden",
          isPreviewTrigger && "cursor-pointer",
          className
        )}
        onClick={() => isPreviewTrigger && setLightbox(true)}
        aria-label={avatarSrc ? "Open avatar preview" : "User avatar"}
      >
        {avatarSrc ? (
          <img
            src={avatarSrc}
            alt={user?.name}
            className="h-full w-full object-cover object-center"
            loading="lazy"
            decoding="async"
          />
        ) : (
          <div className="h-full w-full flex items-center justify-center bg-primary text-primary-foreground font-bold tracking-tighter uppercase select-none">
            {getInitials(user?.name)}
          </div>
        )}

        {/* Editable: camera overlay to change photo */}
        {editable && (
          <>
            <button
              type="button"
              aria-label="Change profile photo"
              disabled={uploading}
              onClick={() => inputRef.current?.click()}
              className={cn(
                "absolute inset-0 flex flex-col items-center justify-center gap-1",
                "bg-black/50 opacity-0 hover:opacity-100 transition-opacity",
                "text-white cursor-pointer disabled:cursor-not-allowed"
              )}
            >
              {uploading ? (
                <svg
                  className="animate-spin h-5 w-5"
                  xmlns="http://www.w3.org/2000/svg"
                  fill="none"
                  viewBox="0 0 24 24"
                >
                  <circle
                    className="opacity-25"
                    cx="12"
                    cy="12"
                    r="10"
                    stroke="currentColor"
                    strokeWidth="4"
                  />
                  <path
                    className="opacity-75"
                    fill="currentColor"
                    d="M4 12a8 8 0 018-8v8z"
                  />
                </svg>
              ) : (
                <svg
                  xmlns="http://www.w3.org/2000/svg"
                  className="h-5 w-5"
                  viewBox="0 0 24 24"
                  fill="currentColor"
                >
                  <path d="M12 15.2A3.2 3.2 0 1 0 12 8.8a3.2 3.2 0 0 0 0 6.4Z" />
                  <path d="M9 2 7.17 4H4a2 2 0 0 0-2 2v12a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V6a2 2 0 0 0-2-2h-3.17L15 2H9Zm3 15a5 5 0 1 1 0-10 5 5 0 0 1 0 10Z" />
                </svg>
              )}
              <span className="text-[10px] font-semibold leading-none">
                {uploading ? "Uploading…" : "Change"}
              </span>
            </button>
            <input
              ref={inputRef}
              type="file"
              accept={ALLOWED_TYPES.join(",")}
              className="hidden"
              onChange={handleFileChange}
            />
          </>
        )}
      </AvatarTrigger>

      {/* Eye button — outside the avatar div so it doesn't get clipped by overflow-hidden */}
      {editable && avatarSrc && (
        <button
          type="button"
          aria-label="Preview photo"
          onClick={() => setLightbox(true)}
          className="absolute bottom-0 right-0 z-10 flex items-center justify-center h-6 w-6 rounded-full bg-black/70 text-white hover:bg-black transition border border-white/20 cursor-pointer"
          title="Preview photo"
        >
          <EyeIcon />
        </button>
      )}

      {/* Lightbox */}
      {lightbox && avatarSrc && (
        <Dialog
          open={lightbox}
          onOpenChange={(open) => !open && setLightbox(false)}
        >
          <DialogContent
            className="w-full sm:max-w-150 h-auto p-0 overflow-hidden"
            showCloseButton={false}
          >
            <DialogTitle className="sr-only">
              {user?.name ? `${user.name}'s avatar` : "Avatar preview"}
            </DialogTitle>
            <DialogDescription className="sr-only">
              Preview of the user avatar image.
            </DialogDescription>
            <div className="relative w-full h-auto flex items-center justify-center">
              <img
                src={avatarSrc}
                alt={user?.name}
                className="w-full h-auto max-h-[80vh] object-contain block"
                loading="lazy"
                decoding="async"
              />

              <DialogClose asChild>
                <button
                  type="button"
                  className="absolute top-4 right-4 text-white bg-black/50 rounded-full p-2 hover:bg-black/80 transition cursor-pointer"
                  aria-label="Close avatar preview"
                  title="Close avatar preview"
                >
                  <CloseIcon />
                </button>
              </DialogClose>
            </div>
          </DialogContent>
        </Dialog>
      )}
    </>
  );
};

export default UserAvatar;
