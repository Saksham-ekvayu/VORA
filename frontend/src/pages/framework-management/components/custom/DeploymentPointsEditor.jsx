/* eslint-disable react/prop-types */
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import Icon from "@/components/custom/Icon";
import { STATUS_PENDING } from "@/utils/commonUtils";

/**
 * DeploymentPointsEditor component
 * Manages adding, removing, and updating names of deployment points.
 *
 * @param {object} props
 * @param {Array} props.points - The list of deployment points
 * @param {Function} props.onChange - Triggered when points change
 * @param {boolean} props.required - Marks field as required
 */
export default function DeploymentPointsEditor({
  points = [],
  onChange,
  required = false,
}) {
  const handlePointNameChange = (index, value) => {
    const nextPoints = points.map((p, i) =>
      i === index ? { ...p, name: value } : p
    );
    onChange(nextPoints);
  };

  const addPoint = () => {
    const nextId = `DP-${String(points.length + 1).padStart(3, "0")}`;
    onChange([
      ...points,
      {
        id: nextId,
        name: "",
        status: STATUS_PENDING,
        path: "",
        weightage: 0,
        remark: "",
      },
    ]);
  };

  const removePoint = (index) => {
    if (points.length > 1) {
      onChange(points.filter((_, i) => i !== index));
    }
  };

  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">
          Deployment Points{" "}
          {required && <span className="text-destructive ml-0.5">*</span>}
          <span className="ml-2 text-xs text-muted-foreground font-normal">
            ({points.length})
          </span>
        </Label>
        <Button
          type="button"
          size="sm"
          onClick={addPoint}
          className="h-7 px-2 text-xs bg-primary/10 text-primary hover:bg-primary/20 border border-primary/20"
        >
          <Icon name="plus" size="14px" />
          <span className="ml-1">Add Point</span>
        </Button>
      </div>

      <div className="space-y-2 max-h-56 overflow-y-auto py-1 pr-1">
        {points.map((point, index) => (
          <div key={point.id || index} className="flex gap-2 items-start">
            <div className="shrink-0 w-6 h-9 flex items-center justify-center text-xs font-medium text-muted-foreground bg-muted rounded">
              {index + 1}
            </div>
            <Input
              value={point.name}
              onChange={(e) => handlePointNameChange(index, e.target.value)}
              className="flex-1"
              placeholder={`Deployment point ${index + 1}...`}
            />
            {points.length > 1 && (
              <Button
                type="button"
                size="icon"
                variant="ghost"
                onClick={() => removePoint(index)}
                className="h-9 w-9 text-destructive hover:text-destructive hover:bg-destructive/10 shrink-0"
                title="Remove point"
              >
                <Icon name="trash" size="16px" />
              </Button>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
