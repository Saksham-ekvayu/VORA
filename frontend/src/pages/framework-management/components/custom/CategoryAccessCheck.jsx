/* eslint-disable react/prop-types */
import Icon from "@/components/custom/Icon";

/**
 * CategoryAccessCheck component
 * Renders loading spinner or empty warning if the user has no approved framework categories.
 *
 * @param {object} props
 * @param {boolean} props.loading - Loading state
 * @param {Array} props.approvedCategories - Transformed accessible categories list
 */
export default function CategoryAccessCheck({ loading, approvedCategories }) {
  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="flex items-center gap-3">
          <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin"></div>
          <span className="text-muted-foreground">
            Loading approved categories...
          </span>
        </div>
      </div>
    );
  }

  if (approvedCategories.length === 0) {
    return (
      <div className="text-center py-12">
        <Icon
          name="warning"
          size="48px"
          className="text-muted-foreground mb-4 mx-auto"
        />
        <h3 className="text-lg font-semibold text-foreground mb-2">
          No Approved Categories
        </h3>
        <p className="text-muted-foreground mb-4">
          You don&apos;t have approved access to any framework categories.
        </p>
        <p className="text-sm text-muted-foreground">
          Please request access to framework categories first.
        </p>
      </div>
    );
  }

  return null;
}
