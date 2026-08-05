/* eslint-disable react/prop-types */

import { AuthContext } from "@/context/authContext/AuthContext";
import { useContext } from "react";
import { Navigate } from "react-router-dom";

const PublicRoute = ({ children }) => {
  const { isAuthenticated } = useContext(AuthContext);

  if (isAuthenticated) {
    return <Navigate to="/" replace />;
  }

  return children;
};

export default PublicRoute;
