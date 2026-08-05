import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import Icon from "@/components/custom/Icon";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Badge } from "@/components/ui/badge";
import {
  Card,
  CardContent,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from "@/components/ui/command";

import assignedFrameworkResponse from "@/data/assignedFrameworkResponse.json";
import userResponse from "@/data/userResponse.json";
import workflowResponse from "@/data/workflowResponse.json";
import { ROLE_AUDITOR } from "@/utils/commonUtils";

const DUMMY_FRAMEWORKS = assignedFrameworkResponse?.data || [];
const DUMMY_AUDITORS = userResponse?.data || [];
const AVAILABLE_AUDITORS = DUMMY_AUDITORS.filter(
  (user) => user.role === ROLE_AUDITOR
);

export default function FrameworkWorkflowSetup() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const workflowId = searchParams.get("id");

  const [activeTab, setActiveTab] = useState("assigned-framework");
  const [configData, setConfigData] = useState({
    "assigned-framework": {
      levels: 1,
      approvalConfig: [{ level: 1, designation: "", auditorId: "" }],
    },
    "deployment-framework": {
      levels: 1,
      approvalConfig: [{ level: 1, designation: "", auditorId: "" }],
    },
  });

  const [selectedFramework, setSelectedFramework] = useState("");
  const [frameworkOpen, setFrameworkOpen] = useState(false);
  const [auditorOpen, setAuditorOpen] = useState({});

  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (workflowId) {
      const existingWorkflow = workflowResponse?.data?.find(
        (w) => w.id === workflowId
      );
      if (existingWorkflow) {
        setSelectedFramework(existingWorkflow.frameworkId);

        setConfigData((prevConfig) => {
          const newConfig = { ...prevConfig };
          if (existingWorkflow["assigned-framework"]) {
            newConfig["assigned-framework"] = {
              levels: existingWorkflow["assigned-framework"].levels,
              approvalConfig: existingWorkflow[
                "assigned-framework"
              ].approvalConfig.map((c) => ({
                level: c.level,
                designation: c.auditor?.designation || "",
                auditorId: c.auditor?.id || "",
              })),
            };
          }
          if (existingWorkflow["deployment-framework"]) {
            newConfig["deployment-framework"] = {
              levels: existingWorkflow["deployment-framework"].levels,
              approvalConfig: existingWorkflow[
                "deployment-framework"
              ].approvalConfig.map((c) => ({
                level: c.level,
                designation: c.auditor?.designation || "",
                auditorId: c.auditor?.id || "",
              })),
            };
          }
          return newConfig;
        });
      }
    }
  }, [workflowId]);

  const selectedFrameworkObj = DUMMY_FRAMEWORKS.find(
    (f) => f.id === selectedFramework
  );

  const currentConfig = configData[activeTab];
  const numLevels = currentConfig.levels;
  const approvalConfig = currentConfig.approvalConfig;

  const handleLevelChange = (e) => {
    const rawValue = e.target.value;

    if (rawValue === "") {
      setConfigData((prev) => ({
        ...prev,
        [activeTab]: { ...prev[activeTab], levels: "" },
      }));
      return;
    }

    const newCount = Number.parseInt(rawValue, 10);
    if (Number.isNaN(newCount) || newCount < 1 || newCount > 5) return;

    setConfigData((prev) => {
      const activeConf = { ...prev[activeTab] };
      activeConf.levels = newCount;
      const currentConfigs = [...activeConf.approvalConfig];
      if (newCount > currentConfigs.length) {
        for (let i = currentConfigs.length; i < newCount; i++) {
          currentConfigs.push({ level: i + 1, designation: "", auditorId: "" });
        }
      } else if (newCount < currentConfigs.length) {
        currentConfigs.length = newCount;
      }
      activeConf.approvalConfig = currentConfigs;
      return { ...prev, [activeTab]: activeConf };
    });
  };

  const updateConfig = (index, field, value) => {
    setConfigData((prev) => {
      const activeConf = { ...prev[activeTab] };
      const currentConfigs = [...activeConf.approvalConfig];
      currentConfigs[index] = { ...currentConfigs[index], [field]: value };
      activeConf.approvalConfig = currentConfigs;
      return { ...prev, [activeTab]: activeConf };
    });
  };

  const toggleAuditorOpen = (idx, open) => {
    setAuditorOpen((prev) => ({ ...prev, [idx]: open }));
  };

  const handleSave = () => {
    setIsSaving(true);
    setTimeout(() => {
      setIsSaving(false);
      toast.success("Workflow Saved!", {
        description: "The approval levels have been configured successfully.",
      });
      setTimeout(() => {}, 500);
    }, 800);
  };

  return (
    <div className="mt-2">
      {/* Header Area */}
      <div className="mb-5 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-xl font-bold tracking-tight text-foreground flex items-center gap-3">
            Workflow Setup
          </h1>
          <p className="mt-2 text-sm text-muted-foreground">
            Configure multi-level approval workflows for your assigned
            compliance frameworks. Define the number of approval levels, set
            specific designations, and assign auditors to ensure a streamlined
            review process.
          </p>
        </div>
        <Button
          onClick={() => navigate("/framework-workflow")}
          size="sm"
          className="flex items-center gap-2"
        >
          <Icon name="arrow-left" size="20px" /> Back
        </Button>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-4">
        {/* Main Form */}
        <div className="lg:col-span-8">
          <Card className="shadow-xs border-primary/20 p-0 gap-0">
            <CardHeader className="bg-muted/30 p-2 border-b border-border">
              <div className="flex items-center justify-between gap-4">
                <CardTitle className="text-lg text-primary font-bold">
                  {workflowId
                    ? "Edit Workflow Configuration"
                    : "New Workflow Configuration"}
                </CardTitle>
                <Tabs
                  value={activeTab}
                  onValueChange={setActiveTab}
                  className="w-100"
                >
                  <TabsList className="grid w-full grid-cols-2">
                    <TabsTrigger value="assigned-framework">
                      Assigned Framework
                    </TabsTrigger>
                    <TabsTrigger value="deployment-framework">
                      Deployment Framework
                    </TabsTrigger>
                  </TabsList>
                </Tabs>
              </div>
            </CardHeader>
            <CardContent className="space-y-8 p-3">
              <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
                <div>
                  <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
                    <span className="text-primary-2 flex">
                      <Icon name="file-text" size={18} />
                    </span>{" "}
                    1. Select Framework
                  </h2>
                  <div className="relative">
                    <Popover
                      open={frameworkOpen}
                      onOpenChange={setFrameworkOpen}
                    >
                      <PopoverTrigger asChild>
                        <Button
                          variant="outline"
                          role="combobox"
                          aria-expanded={frameworkOpen}
                          className="w-full justify-between font-normal text-left"
                        >
                          {selectedFrameworkObj
                            ? `${selectedFrameworkObj.frameworkName} (${selectedFrameworkObj.frameworkVersion})`
                            : "Select a framework..."}
                          <Icon
                            name="chevron-down"
                            className="ml-2 h-4 w-4 shrink-0 opacity-50"
                          />
                        </Button>
                      </PopoverTrigger>
                      <PopoverContent className="w-fit p-0" align="start">
                        <Command>
                          <CommandInput placeholder="Search framework..." />
                          <CommandList>
                            <CommandEmpty>No framework found.</CommandEmpty>
                            <CommandGroup>
                              {DUMMY_FRAMEWORKS.map((fw) => (
                                <CommandItem
                                  key={fw.id}
                                  value={fw.frameworkName}
                                  onSelect={() => {
                                    setSelectedFramework(fw.id);
                                    setFrameworkOpen(false);
                                  }}
                                >
                                  <Icon
                                    name="check"
                                    className={`mr-2 h-4 w-4 ${
                                      selectedFramework === fw.id
                                        ? "opacity-100"
                                        : "opacity-0"
                                    }`}
                                  />
                                  {fw.frameworkName} ({fw.frameworkVersion})
                                </CommandItem>
                              ))}
                            </CommandGroup>
                          </CommandList>
                        </Command>
                      </PopoverContent>
                    </Popover>
                  </div>
                </div>

                <div>
                  <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
                    <span className="text-primary-2 flex">
                      <Icon name="settings" size={18} />
                    </span>{" "}
                    2. Approval Levels
                  </h2>
                  <div className="flex items-center gap-4 p-1 bg-muted/30 rounded border border-border/50">
                    <Label className="text-sm font-medium text-foreground">
                      Number of required approvals:
                    </Label>
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        max={5}
                        value={numLevels}
                        onChange={handleLevelChange}
                        className="w-20 h-7 text-center bg-background"
                      />
                    </div>
                    <span className="text-xs text-muted-foreground italic">
                      (Max 5 levels)
                    </span>
                  </div>
                </div>
              </div>

              <div>
                <h2 className="text-base font-semibold mb-3 flex items-center gap-2">
                  <span className="text-primary-2 flex">
                    <Icon name="user-plus" size={18} />
                  </span>{" "}
                  3. Configure Workflow Chain
                </h2>

                <div className="space-y-4">
                  {approvalConfig.map((config, idx) => {
                    const selectedAuditor = DUMMY_AUDITORS.find(
                      (a) => a.id === config.auditorId
                    );

                    return (
                      <div
                        key={`${config.level}-${idx}`}
                        className="relative flex items-start gap-4 p-4 rounded border border-border bg-background shadow-xs hover:shadow-md transition-shadow duration-300 group"
                      >
                        {/* Left Connector (visual) */}
                        {idx !== approvalConfig.length - 1 && (
                          <div className="hidden sm:block absolute left-8 top-8 -bottom-12 w-0.5 bg-border z-0" />
                        )}

                        <div className="relative z-10 flex items-center justify-center w-8 h-8 rounded-full bg-background shrink-0 mt-1">
                          <div className="flex items-center justify-center w-full h-full rounded-full bg-primary/10 text-primary font-bold border border-primary/20">
                            {config.level}
                          </div>
                        </div>

                        <div className="flex-1 grid grid-cols-1 md:grid-cols-2 gap-4 w-full">
                          <div className="space-y-2">
                            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                              Assign User
                            </Label>
                            <div className="relative">
                              <Popover
                                open={auditorOpen[idx]}
                                onOpenChange={(open) =>
                                  toggleAuditorOpen(idx, open)
                                }
                              >
                                <PopoverTrigger asChild>
                                  <Button
                                    variant="outline"
                                    role="combobox"
                                    aria-expanded={auditorOpen[idx]}
                                    className="w-full justify-between font-normal bg-transparent"
                                  >
                                    {selectedAuditor
                                      ? selectedAuditor.name
                                      : "Select auditor..."}
                                    <Icon
                                      name="chevron-down"
                                      className="ml-2 h-4 w-4 shrink-0 opacity-50"
                                    />
                                  </Button>
                                </PopoverTrigger>
                                <PopoverContent
                                  className="w-75 p-0"
                                  align="start"
                                >
                                  <Command>
                                    <CommandInput placeholder="Search auditor..." />
                                    <CommandList>
                                      <CommandEmpty>
                                        No auditor found.
                                      </CommandEmpty>
                                      <CommandGroup>
                                        {AVAILABLE_AUDITORS.map((auditor) => (
                                          <CommandItem
                                            key={auditor.id}
                                            value={`${auditor.name} ${auditor.id}`}
                                            onSelect={() => {
                                              updateConfig(
                                                idx,
                                                "auditorId",
                                                auditor.id
                                              );
                                              toggleAuditorOpen(idx, false);
                                            }}
                                          >
                                            <Icon
                                              name="check"
                                              className={`mr-2 h-4 w-4 ${
                                                config.auditorId === auditor.id
                                                  ? "opacity-100"
                                                  : "opacity-0"
                                              }`}
                                            />
                                            {auditor.name} ({auditor.role})
                                          </CommandItem>
                                        ))}
                                      </CommandGroup>
                                    </CommandList>
                                  </Command>
                                </PopoverContent>
                              </Popover>
                            </div>
                          </div>
                          <div className="space-y-2">
                            <Label className="text-xs font-medium text-muted-foreground uppercase tracking-wider">
                              Designation
                            </Label>
                            <Input
                              type="text"
                              placeholder="Select an auditor to view designation"
                              value={selectedAuditor?.designation || ""}
                              readOnly
                              className="text-muted-foreground cursor-not-allowed"
                            />
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
              </div>
            </CardContent>

            <CardFooter className="bg-muted/40 flex justify-between items-center border-t border-border p-2">
              <div className="text-sm text-muted-foreground flex items-center gap-2">
                <span className="flex">
                  <Icon name="alert-circle" size={14} />
                </span>{" "}
                Changes apply to future framework submissions.
              </div>
              <Button
                onClick={handleSave}
                disabled={isSaving || !selectedFramework}
                className="flex items-center gap-2 font-medium"
              >
                {isSaving ? (
                  <div className="h-4 w-4 rounded-full border-2 border-white/30 border-t-white animate-spin" />
                ) : (
                  <Icon name="check" size={18} />
                )}
                {isSaving ? "Saving..." : "Save Configuration"}
              </Button>
            </CardFooter>

            {/* Success Overlay */}
          </Card>
        </div>

        {/* Right Sidebar - Info panel */}
        <div className="lg:col-span-4">
          <Card className="bg-linear-to-br from-primary/5 to-primary-2/5 border-primary/20 shadow-xs sticky top-24">
            <CardHeader>
              <CardTitle className="flex items-center gap-2 text-base font-semibold">
                <span className="flex h-6 w-6 items-center justify-center rounded-full bg-primary/20 text-primary text-xs font-bold">
                  i
                </span>{" "}
                How it works
              </CardTitle>
            </CardHeader>
            <CardContent>
              <ul className="space-y-4 text-sm text-muted-foreground">
                <li className="flex gap-3">
                  <div className="mt-0.5 text-primary font-bold">01.</div>
                  <div>
                    <strong>Select Framework:</strong> Choose an assigned
                    framework to configure a new review process, or edit an
                    existing setup.
                  </div>
                </li>
                <li className="flex gap-3">
                  <div className="mt-0.5 text-primary font-bold">02.</div>
                  <div>
                    <strong>Approval Levels:</strong> Define the number of
                    sequential approval steps required before full compliance is
                    granted.
                  </div>
                </li>
                <li className="flex gap-3">
                  <div className="mt-0.5 text-primary font-bold">03.</div>
                  <div>
                    <strong>Configure Workflow Chain:</strong> Map each approval
                    level to a responsible customer user (auditor).
                  </div>
                </li>
              </ul>

              <div className="mt-8 pt-6 border-t border-border/50">
                <div className="flex items-center justify-between mb-3">
                  <h4 className="text-xs font-semibold uppercase tracking-wider text-muted-foreground">
                    Available Auditors
                  </h4>
                  <Link
                    to="/profiles"
                    className="text-xs text-primary hover:underline flex items-center gap-1 font-medium"
                  >
                    <Icon name="plus" size={12} />
                    Add Auditor
                  </Link>
                </div>
                <div className="flex flex-wrap gap-2">
                  {AVAILABLE_AUDITORS.map((auditor) => (
                    <Badge
                      key={auditor.id}
                      variant="outline"
                      className="bg-muted"
                    >
                      {auditor.name}
                    </Badge>
                  ))}
                </div>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </div>
  );
}
