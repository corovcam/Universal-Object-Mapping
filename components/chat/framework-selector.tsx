"use client";

import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { FRAMEWORKS } from "@/lib/frameworks";
import type { FrameworkType } from "@/lib/types";

interface FrameworkSelectorProps {
  value: FrameworkType | undefined;
  onChange: (value: FrameworkType) => void;
  label: string;
  placeholder?: string;
  disabled?: boolean;
  excludeFramework?: FrameworkType;
}

export function FrameworkSelector({
  value,
  onChange,
  label,
  placeholder = "Select framework",
  disabled = false,
  excludeFramework,
}: FrameworkSelectorProps) {
  const availableFrameworks = FRAMEWORKS.filter(
    (f) => f.id !== excludeFramework
  );

  return (
    <div className="flex flex-col gap-1.5">
      <label className="text-xs font-medium text-muted-foreground">
        {label}
      </label>
      <Select
        value={value}
        onValueChange={(v) => onChange(v as FrameworkType)}
        disabled={disabled}
      >
        <SelectTrigger className="w-full min-w-[180px] h-9 text-sm">
          <SelectValue placeholder={placeholder} />
        </SelectTrigger>
        <SelectContent>
          {availableFrameworks.map((framework) => (
            <SelectItem key={framework.id} value={framework.id}>
              <div className="flex items-center gap-2">
                <div
                  className="w-2 h-2 rounded-full"
                  style={{ backgroundColor: framework.color }}
                />
                <span>{framework.name}</span>
              </div>
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
    </div>
  );
}
