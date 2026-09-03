/* eslint-disable react/prop-types */

import { useState, useEffect, useCallback, useMemo } from "react";
import { userProfile } from "@/services/userService";
import { useAuth } from "@/context/authContext/useAuth";
import { ProfileContext } from "@/context/profileContext/useProfile";

export function ProfileProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);
      const response = await userProfile();
      if (!response?.success && response?.message) {
        setError(response.message);
      } else {
        setProfile(response.data);
      }
    } catch (err) {
      console.error("Profile fetch error:", err);
      setError(err?.message || "Failed to fetch profile");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) fetchProfile();
  }, [isAuthenticated, fetchProfile]);

  const value = useMemo(
    () => ({ profile, loading, error, fetchProfile }),
    [profile, loading, error, fetchProfile]
  );

  return (
    <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
  );
}
