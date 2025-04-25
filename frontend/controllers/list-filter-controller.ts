import { Controller } from "@hotwired/stimulus";
import { camelCase } from "change-case";

class BacklinkController extends Controller {
  // Targets
  static targets = ["option", "item", "count"];
  private readonly countTarget?: HTMLElement;
  private readonly countTargets?: HTMLElement[];
  private readonly optionTarget!: HTMLElement;
  private readonly optionTargets!: HTMLElement[];
  private readonly itemTarget!: HTMLElement;
  private readonly itemTargets!: HTMLElement[];

  // Values
  static values = {
    itemVisibleClasses: { type: String, default: "" },
    itemHiddenClasses: { type: String, default: "tw-hidden" },
    optionActiveClasses: { type: String, default: "tw-font-bold" },
    optionPassiveClasses: { type: String, default: "" },
    selected: Object,
  };
  private itemVisibleClassesValue: string | undefined;
  private itemHiddenClassesValue: string | undefined;
  private optionActiveClassesValue: string | undefined;
  private optionPassiveClassesValue: string | undefined;
  private selectedValue?: {
    [camelCaseAttr: string]: string | number;
  };

  connect() {
    this.applyFilters();
  }

  toggleForAttr({ params: { value, attr } }: any) {
    if (typeof this.selectedValue === "undefined") {
      this.selectedValue = {};
    }

    const currentValue = this.selectedValue[attr];
    const newValue = currentValue === value ? "__ALL__" : value;

    this.selectedValue = {
      ...this.selectedValue,
      [attr]: newValue,
    };

    const optionButton = this.optionTargets.find(
      (el) => el.dataset.listFilterAttrParam === attr
    );
    if (optionButton) {
      optionButton.textContent =
        newValue === value ? "Show All Groups" : "Show Online Groups Only";
    }

    this.applyFilters();
  }

  selectedValueChanged() {
    this.applyFilters();
  }

  applyFilters() {
    let count = 0;

    if (
      typeof this.selectedValue === "undefined" ||
      !Object.keys(this.selectedValue).length
    ) {
      count = this.itemTargets.length;
    } else {
      for (const camelCaseAttr in this.selectedValue) {
        const filterValue = this.selectedValue[camelCaseAttr];

        for (const item of this.itemTargets) {
          if (
            item.dataset[camelCaseAttr] === filterValue ||
            filterValue === "__ALL__"
          ) {
            count++;
            if (this.itemVisibleClassesValue?.length)
              item.classList.add(...this.itemVisibleClassesValue.split(" "));
            if (this.itemHiddenClassesValue?.length)
              item.classList.remove(...this.itemHiddenClassesValue.split(" "));
          } else {
            if (this.itemHiddenClassesValue?.length)
              item.classList.add(...this.itemHiddenClassesValue.split(" "));
            if (this.itemVisibleClassesValue?.length)
              item.classList.remove(...this.itemVisibleClassesValue.split(" "));
          }
        }

        for (const option of this.optionTargets) {
          if (option.dataset.listFilterAttrParam === camelCaseAttr) {
            if (option.dataset.listFilterValueParam === filterValue) {
              if (this.optionActiveClassesValue?.length)
                option.classList.add(
                  ...this.optionActiveClassesValue.split(" ")
                );
              if (this.optionPassiveClassesValue?.length)
                option.classList.remove(
                  ...this.optionPassiveClassesValue.split(" ")
                );
            } else {
              if (this.optionPassiveClassesValue?.length)
                option.classList.add(
                  ...this.optionPassiveClassesValue.split(" ")
                );
              if (this.optionActiveClassesValue?.length)
                option.classList.remove(
                  ...this.optionActiveClassesValue.split(" ")
                );
            }
          }
        }
      }
    }

    if (this.countTargets?.length) {
      const isAll =
        !this.selectedValue ||
        Object.values(this.selectedValue).includes("__ALL__");
      const groupLabel = count === 1 ? "reading group" : "reading groups";

      this.countTargets.forEach((target) => {
        target.textContent = isAll
          ? `Showing all ${count} ${groupLabel}`
          : `Showing ${count} ${groupLabel}`;
      });
    }
  }
}

export default BacklinkController;
