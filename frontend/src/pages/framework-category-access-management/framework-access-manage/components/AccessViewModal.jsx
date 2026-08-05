/* eslint-disable react/prop-types */

import { RecordTimelineViewModal } from "@/components/custom/modal";

export default function AccessViewModal({ accessRecord, onClose }) {
  if (!accessRecord) return null;

  const getTimelineEvents = () => {
    const events = [];

    if (accessRecord.approval) {
      events.push({
        id: "approval",
        title: "Access Approved",
        date: accessRecord.approval.approvedAt,
        actor: accessRecord.approval.approvedBy?.name,
        email: accessRecord.approval.approvedBy?.email,
        icon: "check-circle",
        color: "text-emerald-600 dark:text-emerald-400",
        bgColor: "bg-emerald-100 dark:bg-emerald-950/50",
      });
    }

    if (accessRecord.rejection) {
      events.push({
        id: "rejection",
        title: "Access Rejected",
        date: accessRecord.rejection.rejectedAt,
        actor: accessRecord.rejection.rejectedBy?.name,
        email: accessRecord.rejection.rejectedBy?.email,
        reason: accessRecord.rejection.reason,
        icon: "x-circle",
        color: "text-rose-600 dark:text-rose-400",
        bgColor: "bg-rose-100 dark:bg-rose-950/50",
      });
    }

    if (accessRecord.revocation) {
      events.push({
        id: "revocation",
        title: "Access Revoked",
        date: accessRecord.revocation.revokedAt,
        actor: accessRecord.revocation.revokedBy?.name,
        email: accessRecord.revocation.revokedBy?.email,
        icon: "alert-circle",
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-100 dark:bg-orange-950/50",
      });
    }

    return events.sort((a, b) => new Date(b.date) - new Date(a.date));
  };

  const infoItems = [];
  if (accessRecord.createdAt) {
    infoItems.push({
      label: "Requested",
      value: new Date(accessRecord.createdAt).toLocaleString(),
      icon: "clock",
    });
  }
  if (accessRecord.requestedBy) {
    infoItems.push({
      label: "By",
      value: accessRecord.requestedBy,
      icon: "user",
    });
  }

  const leftEntity = {
    title: "Expert",
    name: accessRecord.expert?.name,
    email: accessRecord.expert?.email,
    role: accessRecord.expert?.role,
    icon: "user",
  };

  const rightEntity = {
    title: "Framework",
    name: accessRecord.frameworkCategory?.frameworkCategoryName,
    code: accessRecord.frameworkCategory?.frameworkCode,
    isActive: accessRecord.frameworkCategory?.isActive,
    icon: "shield",
  };

  const timestamps = [
    { label: "Created On", date: accessRecord.createdAt },
    { label: "Last Updated On", date: accessRecord.updatedAt },
  ];

  return (
    <RecordTimelineViewModal
      isOpen={true}
      onClose={onClose}
      title="Framework Access Details"
      recordId={accessRecord.id}
      status={accessRecord.status}
      infoItems={infoItems}
      leftEntity={leftEntity}
      rightEntity={rightEntity}
      description={accessRecord.frameworkCategory?.description}
      timelineEvents={getTimelineEvents()}
      timestamps={timestamps}
    />
  );
}
