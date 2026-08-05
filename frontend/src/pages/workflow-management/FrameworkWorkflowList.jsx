import { useNavigate } from "react-router-dom";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";
import { Badge } from "@/components/ui/badge";
import DataTable from "@/components/data-table/DataTable";
import ActionDropdown from "@/components/custom/ActionDropdown";
import UserMiniCard from "@/components/custom/UserMiniCard";
import { useTableData } from "@/components/data-table/hooks/useTableData";

import workflowResponse from "@/data/workflowResponse.json";
import { formatDateWithMonthNameAndTime } from "@/utils/dateFormatter";
import FrameworkMiniCard from "@/components/custom/FrameworkMiniCard";

// Mock API fetch function
const getAllWorkflows = async (params) => {
  // Simulate network delay
  await new Promise((resolve) => {
    setTimeout(resolve, 300);
  });

  const { page = 1, limit = 10, search = "" } = params || {};

  let filteredData = workflowResponse?.data || [];

  if (search) {
    filteredData = filteredData.filter((w) =>
      w.framework.frameworkName.toLowerCase().includes(search.toLowerCase())
    );
  }

  const totalItems = filteredData.length;
  const totalPages = Math.ceil(totalItems / limit) || 1;
  const startIndex = (page - 1) * limit;
  const paginatedData = filteredData.slice(startIndex, startIndex + limit);

  return {
    success: true,
    data: paginatedData,
    pagination: {
      currentPage: page,
      totalPages,
      totalItems,
      itemsPerPage: limit,
      hasNextPage: page < totalPages,
      hasPrevPage: page > 1,
    },
  };
};

export default function FrameworkWorkflowList() {
  const navigate = useNavigate();

  const {
    data: workflows,
    loading,
    emptyMessage,
    pagination,
    searchTerm,
    sortConfig,
    onSearch: handleSearch,
    onSort: handleSort,
  } = useTableData(getAllWorkflows, {
    defaultLimit: 10,
    defaultSortBy: "createdAt",
    defaultSortOrder: "desc",
    emptyMessage: "No configured workflows found.",
  });

  const renderLevelsColumn = (configData) => {
    if (!configData?.levels)
      return <span className="text-muted-foreground text-sm">-</span>;
    return (
      <TooltipProvider delayDuration={100}>
        <Tooltip>
          <TooltipTrigger asChild>
            <div className="flex items-center gap-2 text-sm font-medium cursor-help w-max">
              <div className="h-6 w-6 rounded-full bg-primary/10 text-primary flex items-center justify-center">
                {configData.levels}
              </div>
              Level(s)
            </div>
          </TooltipTrigger>
          <TooltipContent
            side="top"
            className="bg-background text-foreground border border-border shadow-md max-w-sm p-3"
          >
            <div className="font-semibold text-xs mb-2 text-muted-foreground uppercase tracking-wider">
              Assigned Auditors
            </div>
            <div className="flex flex-col gap-3">
              {configData.approvalConfig?.map((config, idx) => (
                <div
                  key={`${config.level}-${idx}`}
                  className="flex items-center gap-3"
                >
                  <Badge
                    variant="secondary"
                    className="text-[10px] whitespace-nowrap h-5 px-1.5 min-w-15 justify-center text-muted-foreground bg-muted"
                  >
                    Level {config.level}
                  </Badge>
                  {config.auditor ? (
                    <UserMiniCard
                      name={config.auditor.name}
                      email={config.auditor.email}
                      avatar={config.auditor.avatar}
                    />
                  ) : (
                    <span className="text-xs text-muted-foreground italic">
                      Not Assigned
                    </span>
                  )}
                </div>
              ))}
            </div>
          </TooltipContent>
        </Tooltip>
      </TooltipProvider>
    );
  };

  const columns = [
    {
      key: "frameworkName",
      label: "Framework",
      sortable: false,
      render: (value, row) => (
        <FrameworkMiniCard
          name={row.framework?.frameworkName}
          description={row.framework?.frameworkVersion}
        />
      ),
    },
    {
      key: "assignedLevels",
      label: "Assigned Levels",
      sortable: false,
      render: (value, row) => renderLevelsColumn(row["assigned-framework"]),
    },
    {
      key: "deploymentLevels",
      label: "Deployment Levels",
      sortable: false,
      render: (value, row) => renderLevelsColumn(row["deployment-framework"]),
    },
    {
      key: "createdAt",
      label: "Created On",
      sortable: true,
      render: (value) => (
        <span className="text-sm whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
    {
      key: "updatedAt",
      label: "Updated On",
      sortable: true,
      render: (value) => (
        <span className="text-sm whitespace-nowrap">
          {formatDateWithMonthNameAndTime(value)}
        </span>
      ),
    },
  ];

  const renderActions = (row) => {
    const actions = [
      {
        id: `edit-${row.id}`,
        label: "Edit Setup",
        icon: "edit",
        onClick: () => navigate(`/framework-workflow/setup?id=${row.id}`),
      },
    ];

    return (
      <div className="flex justify-center">
        <ActionDropdown actions={actions} />
      </div>
    );
  };

  const getHeaderActions = () => [
    {
      type: "button",
      label: "Setup New Workflow",
      icon: "plus",
      onClick: () => navigate("/framework-workflow/setup"),
    },
  ];

  return (
    <div className="mt-2">
      <DataTable
        entityName="Workflows"
        columns={columns}
        data={workflows}
        loading={loading}
        onSearch={handleSearch}
        onSort={handleSort}
        sortConfig={sortConfig}
        searchTerm={searchTerm}
        pagination={pagination}
        renderActions={renderActions}
        headerActions={getHeaderActions()}
        searchPlaceholder="Search framework workflows..."
        emptyMessage={emptyMessage}
      />
    </div>
  );
}
