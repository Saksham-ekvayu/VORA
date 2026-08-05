/* eslint-disable react/prop-types */

import { useState, useEffect, useCallback, useMemo } from "react";
import { userProfile } from "@/services/userService";
import { useAuth } from "@/context/authContext/useAuth";
import { ProfileContext } from "@/context/profileContext/useProfile";

export function ProfileProvider({ children }) {
  const { isAuthenticated } = useAuth();
  const [profile, setProfile] = useState(null);
  const [loading, setLoading] = useState(true);

  const fetchProfile = useCallback(async () => {
    try {
      setLoading(true);
      const response = await userProfile();
      setProfile(response.data);
    } catch (err) {
      console.error("Profile fetch error:", err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) fetchProfile();
  }, [isAuthenticated, fetchProfile]);

  const value = useMemo(
    () => ({ profile, loading, fetchProfile }),
    [profile, loading, fetchProfile]
  );

  return (
    <ProfileContext.Provider value={value}>{children}</ProfileContext.Provider>
  );
}
