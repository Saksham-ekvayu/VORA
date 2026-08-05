import { Toaster } from "../ui/sonner";

export default function AppToaster() {
  return (
    <Toaster
      position="top-center"
      closeButton
      duration={3000}
      toastOptions={{
        classNames: {
          toast: "!rounded",
          title: "!text-foreground !font-medium",
          description: "!text-muted-foreground",
          success: "!border-l-4 !border-l-primary",
          error: "!border-l-4 !border-l-destructive",
          warning: "!border-l-4 !border-l-yellow-500",
          info: "!border-l-4 !border-l-blue-500",
        },
      }}
    />
  );
}
