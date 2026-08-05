/* eslint-disable react/prop-types */

import { RecordTimelineViewModal } from "@/components/custom/modal";

export default function AssignmentViewModal({ assignment, onClose }) {
  if (!assignment) return null;

  const getTimelineEvents = () => {
    const events = [];

    if (
      assignment.assignment?.assignedBy &&
      assignment.assignment?.assignedAt
    ) {
      events.push({
        id: "assigned",
        title: "Framework Assigned",
        date: assignment.assignment.assignedAt,
        actor: assignment.assignment.assignedBy?.name,
        email: assignment.assignment.assignedBy?.email,
        icon: "check-circle",
        color: "text-emerald-600 dark:text-emerald-400",
        bgColor: "bg-emerald-100 dark:bg-emerald-950/50",
      });
    }

    if (assignment.revocation?.revokedBy) {
      events.push({
        id: "revocation",
        title: "Assignment Revoked",
        date: assignment.revocation.revokedAt,
        actor: assignment.revocation.revokedBy?.name,
        email: assignment.revocation.revokedBy?.email,
        icon: "alert-circle",
        color: "text-orange-600 dark:text-orange-400",
        bgColor: "bg-orange-100 dark:bg-orange-950/50",
      });
    }

    return events.sort((a, b) => new Date(b.date) - new Date(a.date));
  };

  const infoItems = [];
  if (assignment.assignment?.assignedAt) {
    infoItems.push({
      label: "Assigned",
      value: new Date(assignment.assignment.assignedAt).toLocaleString(),
      icon: "clock",
    });
  }

  const leftEntity = {
    title: "Customer",
    name: assignment.customer?.name,
    email: assignment.customer?.email,
    icon: "users",
  };

  const rightEntity = {
    title: "Framework",
    name: assignment.frameworkName,
    code: assignment.frameworkCode,
    version: assignment.frameworkVersion,
    icon: "shield",
  };

  const timestamps = [
    { label: "Assigned On", date: assignment.createdAt },
    { label: "Last Updated On", date: assignment.updatedAt },
  ];

  return (
    <RecordTimelineViewModal
      isOpen={true}
      onClose={onClose}
      title="Framework Assignment Details"
      recordId={assignment.id}
      status={assignment.status}
      infoItems={infoItems}
      leftEntity={leftEntity}
      rightEntity={rightEntity}
      timelineEvents={getTimelineEvents()}
      timestamps={timestamps}
    />
  );
}
