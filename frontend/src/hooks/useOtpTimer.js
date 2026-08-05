import { useState, useEffect, useCallback } from "react";
import { resendOTP } from "@/services/authService";
import { toast } from "sonner";

/**
 * useOtpTimer - Hook to manage OTP resend cooldown timer and api call
 *
 * @param {string} email - Email to resend OTP to
 * @param {number} initialCooldown - Initial cooldown timer in seconds
 */
export default function useOtpTimer(email, initialCooldown = 60) {
  const [resendCooldown, setResendCooldown] = useState(0);
  const [isResendOtpLoading, setIsResendOtpLoading] = useState(false);

  useEffect(() => {
    if (resendCooldown > 0) {
      const timer = setTimeout(() => {
        setResendCooldown((prev) => prev - 1);
      }, 1000);
      return () => clearTimeout(timer);
    }
  }, [resendCooldown]);

  const handleResendOTP = useCallback(async () => {
    if (resendCooldown > 0 || !email) return;

    setIsResendOtpLoading(true);
    try {
      const response = await resendOTP(email);
      toast.success(
        response.message || "A new OTP has been sent to your email."
      );
      setResendCooldown(initialCooldown);
    } catch (error) {
      console.error(error.message);
      toast.error(error.message || "Failed to resend OTP. Please try again.");
    } finally {
      setIsResendOtpLoading(false);
    }
  }, [email, resendCooldown, initialCooldown]);

  return {
    resendCooldown,
    isResendOtpLoading,
    handleResendOTP,
  };
}
