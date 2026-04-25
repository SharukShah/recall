"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Plus, X } from "lucide-react";
import type { LociCreateRequest } from "@/types/loci";

interface LociFormProps {
  onSubmit: (data: LociCreateRequest) => void;
  disabled?: boolean;
}

const PALACE_THEMES = [
  { value: "apartment", label: "My Apartment" },
  { value: "library", label: "A Library" },
  { value: "garden", label: "A Garden" },
  { value: "nature_trail", label: "A Nature Trail" },
  { value: "auto", label: "Let AI Choose" },
];

export function LociForm({ onSubmit, disabled }: LociFormProps) {
  const [title, setTitle] = useState("");
  const [items, setItems] = useState<string[]>(["", "", ""]);
  const [palaceTheme, setPalaceTheme] = useState("auto");

  const addItem = () => {
    if (items.length < 20) {
      setItems([...items, ""]);
    }
  };

  const removeItem = (index: number) => {
    if (items.length > 3) {
      setItems(items.filter((_, i) => i !== index));
    }
  };

  const updateItem = (index: number, value: string) => {
    const updated = [...items];
    updated[index] = value;
    setItems(updated);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const filteredItems = items.filter((item) => item.trim() !== "");
    if (filteredItems.length < 3 || filteredItems.length > 20) {
      alert("Please enter between 3 and 20 items");
      return;
    }
    if (!title.trim()) {
      alert("Please enter a title");
      return;
    }
    onSubmit({
      items: filteredItems,
      title: title.trim(),
      palace_theme: palaceTheme === "auto" ? undefined : palaceTheme,
    });
  };

  const isValid = items.filter((i) => i.trim()).length >= 3 && title.trim() !== "";

  return (
    <Card>
      <CardHeader>
        <CardTitle>Create Memory Palace</CardTitle>
      </CardHeader>
      <CardContent>
        <form onSubmit={handleSubmit} className="space-y-6">
          <div className="space-y-2">
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="e.g., OSI Model Layers"
              disabled={disabled}
            />
          </div>

          <div className="space-y-2">
            <Label htmlFor="palace_theme">Palace Theme</Label>
            <Select value={palaceTheme} onValueChange={setPalaceTheme} disabled={disabled}>
              <SelectTrigger id="palace_theme">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                {PALACE_THEMES.map((theme) => (
                  <SelectItem key={theme.value} value={theme.value}>
                    {theme.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </div>

          <div className="space-y-3">
            <div className="flex items-center justify-between">
              <Label>Items to Memorize ({items.filter((i) => i.trim()).length}/20)</Label>
              <Button
                type="button"
                variant="outline"
                size="sm"
                onClick={addItem}
                disabled={disabled || items.length >= 20}
              >
                <Plus className="h-4 w-4 mr-1" />
                Add Item
              </Button>
            </div>
            <div className="space-y-2">
              {items.map((item, index) => (
                <div key={index} className="flex gap-2">
                  <Input
                    value={item}
                    onChange={(e) => updateItem(index, e.target.value)}
                    placeholder={`Item ${index + 1}`}
                    disabled={disabled}
                  />
                  {items.length > 3 && (
                    <Button
                      type="button"
                      variant="ghost"
                      size="icon"
                      onClick={() => removeItem(index)}
                      disabled={disabled}
                    >
                      <X className="h-4 w-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          </div>

          <Button type="submit" disabled={!isValid || disabled} className="w-full">
            Generate Memory Palace
          </Button>
        </form>
      </CardContent>
    </Card>
  );
}
