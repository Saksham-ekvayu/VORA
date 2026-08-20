/* eslint-disable react/prop-types */

/**
 * Modern Icon Component using React Icons
 * Provides professional icons from react-icons library
 */

import {
  // Navigation & Dashboard
  MdDashboard,
  MdHome,
  MdMenu,
  MdCategory,
  MdAssignment,
  MdAssignmentInd,
  MdBusiness,
  MdAttachFile,
  MdVpnKey,
  MdCloudUpload,

  // Documents & Files
  MdDescription,
  MdFolder,
  MdFolderOpen,
  MdInsertDriveFile,
  MdUpload,
  MdPictureAsPdf,
  MdTableChart,

  // Users & Profile
  MdAccountCircle,

  // Actions
  MdAdd,
  MdEdit,
  MdDelete,
  MdClose,
  MdRemove,
  MdVisibility,
  MdVisibilityOff,
  MdContentCopy,
  MdPlayArrow,
  MdHistory,

  // Status & Alerts
  MdCheck,
  MdCheckCircle,
  MdCancel,
  MdWarning,
  MdError,
  MdInfo,
  MdInfoOutline,

  // Arrows & Navigation
  MdArrowUpward,
  MdArrowDownward,
  MdKeyboardArrowDown,

  // Time & Calendar
  MdAccessTime,
  MdCalendarToday,
  MdHourglassEmpty,

  // Communication
  MdEmail,
  MdPhone,
  MdMessage,
  MdNotifications,

  // Settings & Tools
  MdBuild,
  MdSearch,
  MdAnalytics,

  // Security & Framework
  MdSecurity,
  MdLock,
  MdShield,
  MdVerifiedUser,
  MdVerified,

  // Charts & Reports
  MdBarChart,
  MdShowChart,

  // Theme
  MdLightMode,
  MdDarkMode,

  // Misc
  MdStar,
  MdFavorite,
  MdLink,
  MdLabel,
  MdLightbulb,
  MdPowerSettingsNew,
  MdList,
  MdBook,
  MdWork,
  MdLocationOn,
  MdLayers,
  MdInbox,
} from "react-icons/md";
import { TbRefresh } from "react-icons/tb";
import { TiPin } from "react-icons/ti";
import {
  // Additional icons from Feather Icons
  FiActivity,
  FiClock,
  FiUser,
  FiUsers,
  FiUserPlus,
  FiUserMinus,
  FiUserCheck,
  FiDownload,
  FiUploadCloud,
  FiLoader,
  FiChevronUp,
  FiChevronRight,
  FiGitMerge,
  FiAlertCircle,
  FiGlobe,
  FiBriefcase,
  FiSearch,
  FiSettings,
  FiTrendingUp,
  FiTrendingDown,
} from "react-icons/fi";

import {
  // Heroicons for additional variety
  HiOutlineDocumentText,
  HiOutlineClipboardList,
  HiDotsVertical,
} from "react-icons/hi";
import {
  FaAngleDoubleLeft,
  FaAngleDoubleRight,
  FaAngleLeft,
  FaAngleRight,
  FaBuilding,
  FaFolderOpen,
  FaGitAlt,
  FaRocket,
} from "react-icons/fa";
import { RiRobot2Fill } from "react-icons/ri";

import { IoKeySharp } from "react-icons/io5";
import { IoIosSend, IoMdCloseCircle } from "react-icons/io";

// Icon mapping from old names to React Icons components
const iconMap = {
  // Navigation icons
  dashboard: MdDashboard,
  home: MdHome,
  menu: MdMenu,
  category: MdCategory,
  assignment: MdAssignment,
  "assignment-ind": MdAssignmentInd,
  business: MdBusiness,
  "attach-file": MdAttachFile,
  "vpn-key": MdVpnKey,
  "cloud-upload": MdCloudUpload,
  "map-pin": MdLocationOn,

  // Document icons
  document: MdDescription,
  file: MdInsertDriveFile,
  docs: HiOutlineDocumentText,
  "file-text": HiOutlineDocumentText,

  // Upload/Download icons
  upload: MdUpload,
  download: FiDownload,
  send: IoIosSend,
  "upload-cloud": FiUploadCloud,

  // Search/Analysis icons
  search: FiSearch,
  analyze: MdAnalytics,
  analytics: MdShowChart,

  // Security & Framework icons
  shield: MdShield,
  "shield-check": MdVerified,
  security: MdSecurity,
  lock: MdLock,
  eye: MdVisibility,
  "eye-off": MdVisibilityOff,
  key: IoKeySharp,

  // Chart/Analytics icons
  chart: MdBarChart,
  "trending-up": FiTrendingUp,
  "trending-down": FiTrendingDown,

  // Settings/Config icons
  gear: MdBuild,
  settings: FiSettings,

  // Book/Documentation icons
  book: MdBook,

  // User/Profile icons
  user: FiUser,
  users: FiUsers,
  profile: MdAccountCircle,
  "user-plus": FiUserPlus,
  "user-minus": FiUserMinus,
  "user-check": FiUserCheck,

  // Status icons
  check: MdCheck,
  checkmark: MdCheck,
  success: MdCheckCircle,
  "check-circle": MdCheckCircle,
  "close-circle": IoMdCloseCircle,
  warning: MdWarning,
  error: MdError,
  info: MdInfoOutline,
  "x-circle": MdCancel,
  "alert-circle": FiAlertCircle,
  loader: FiLoader,
  inbox: MdInbox,
  ban: MdCancel, // Using MdCancel for ban/revoke actions

  // Arrow icons
  "arrow-up": MdArrowUpward,
  "arrow-down": MdArrowDownward,
  "arrow-left": FaAngleLeft,
  "arrow-right": FaAngleRight,
  "chevron-down": MdKeyboardArrowDown,
  "chevron-up": FiChevronUp,
  "chevron-right": FiChevronRight,
  "left-dubble-arrow": FaAngleDoubleLeft,
  "right-dubble-arrow": FaAngleDoubleRight,

  // Action icons
  plus: MdAdd,
  add: MdAdd,
  minus: MdRemove,
  close: MdClose,
  x: MdClose,
  delete: MdDelete,
  trash: MdDelete,
  edit: MdEdit,
  "more-vertical": HiDotsVertical,
  copy: MdContentCopy,
  play: MdPlayArrow,

  // Time icons
  clock: FiClock,
  time: MdAccessTime,
  calendar: MdCalendarToday,
  hourglass: MdHourglassEmpty,
  history: MdHistory,

  // Folder icons
  folder: MdFolder,
  "folder-open": MdFolderOpen,

  // List icons
  list: MdList,

  // Communication icons
  mail: MdEmail,
  email: MdEmail,
  phone: MdPhone,
  message: MdMessage,
  "message-square": MdMessage,
  notification: MdNotifications,

  // Theme icons
  sun: MdLightMode,
  moon: MdDarkMode,

  // Misc icons
  star: MdStar,
  heart: MdFavorite,
  link: MdLink,
  tag: MdLabel,
  lightbulb: MdLightbulb,
  power: MdPowerSettingsNew,
  layers: MdLayers,

  // Compliance/Audit specific
  audit: MdSearch,
  compliance: MdVerifiedUser,
  framework: MdWork,
  report: HiOutlineClipboardList,

  // File type icons
  pdf: MdPictureAsPdf,
  doc: MdDescription,
  excel: MdTableChart,
  ppt: MdDescription,
  csv: MdTableChart,
  zip: MdFolder,
  refresh: TbRefresh,
  building: FaBuilding,

  // Ai icons
  "ai-bot": RiRobot2Fill,

  // Activity specific
  activity: FiActivity,

  // Git/Merge icons
  "git-merge": FiGitMerge,
  git: FaGitAlt,

  // Additional Layout Icons
  globe: FiGlobe,
  briefcase: FiBriefcase,

  // Additional icons
  rocket: FaRocket,
  alert: MdWarning,
  pin: TiPin,
  "open-folder": FaFolderOpen,
};

export default function Icon({
  name,
  size = "1em",
  style = {},
  className = "",
}) {
  // Get the icon component from the map
  const IconComponent = iconMap[name] || MdInfo;

  // Convert size to number if it's a string with 'px'
  const iconSize =
    typeof size === "string" && size.includes("px")
      ? Number.parseInt(size.replace("px", ""))
      : size;

  return (
    <IconComponent
      className={className}
      style={{
        fontSize: iconSize,
        width: iconSize,
        height: iconSize,
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        ...style,
      }}
      aria-label={name}
    />
  );
}
