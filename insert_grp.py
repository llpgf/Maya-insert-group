import maya.cmds as cmds
import maya.mel as mel


class InsertGroupTool:
    """
    Maya tool for inserting groups between objects and their parents.
    Allows users to create multiple groups with custom names and pivot options.
    """
    
    def __init__(self):
        self.window_name = "InsertGroupTool"
        self.selected_objects = []
        self.group_fields = []
        self.object_list = None
        self.groups_layout = None

    def create_ui(self):
        """Create the main UI window."""
        if cmds.window(self.window_name, exists=True):
            cmds.deleteUI(self.window_name)

        cmds.window(self.window_name, title="Insert Group Tool", widthHeight=(400, 500))
        main_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=5, columnOffset=["both", 5])

        # Header
        cmds.text(label="Insert Group Tool", height=30)
        cmds.separator(height=10)

        # Selected objects management
        cmds.frameLayout(label="Selected Objects", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        self.object_list = cmds.textScrollList(allowMultiSelection=True, height=120, 
                                              selectCommand=self.on_object_selected)
        
        button_layout = cmds.rowLayout(numberOfColumns=3, columnWidth3=(100, 100, 100), 
                                      adjustableColumn=3, columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0)])
        cmds.button(label="Add Selected", command=self.add_selected)
        cmds.button(label="Remove Selected", command=self.remove_selected)
        cmds.button(label="Clear All", command=self.clear_all)
        cmds.setParent('..')  # Exit rowLayout
        cmds.setParent('..')  # Exit columnLayout
        cmds.setParent('..')  # Exit frameLayout

        # Group management
        cmds.frameLayout(label="Group to Insert", collapsable=True, collapse=False)
        self.groups_layout = cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        self.add_group_field()
        cmds.setParent('..')  # Exit columnLayout
        cmds.setParent('..')  # Exit frameLayout

        # Naming options
        cmds.frameLayout(label="Naming Options", collapsable=True, collapse=False)
        cmds.columnLayout(adjustableColumn=True, rowSpacing=3)
        
        cmds.text(label="Group naming based on:")
        self.naming_radio = cmds.radioButtonGrp(numberOfRadioButtons=3, 
                                               label1="Custom Name", 
                                               label2="Upper Group", 
                                               label3="Lower Group",
                                               select=1)
        
        cmds.text(label="Naming style:")
        self.style_radio = cmds.radioButtonGrp(numberOfRadioButtons=2, 
                                              label1="Prefix", 
                                              label2="Suffix",
                                              select=1)
        
        cmds.setParent('..')  # Exit columnLayout
        cmds.setParent('..')  # Exit frameLayout



        # Execute button
        cmds.separator(height=10)
        cmds.button(label="Insert Groups", command=self.insert_groups, height=40)

        cmds.showWindow()

    def add_group_field(self, *args):
        """Add a new group field row to the UI."""
        row = cmds.rowLayout(numberOfColumns=4, parent=self.groups_layout, 
                            adjustableColumn=2, columnAttach=[(1, 'both', 0), (2, 'both', 0), (3, 'both', 0), (4, 'both', 0)])
        field = cmds.textField(parent=row, placeholderText="Group Name", width=150)
        checkbox = cmds.checkBox(label="Object Pivot", value=True, parent=row, width=80)
        cmds.setParent('..')  # Exit rowLayout
        self.group_fields.append((field, checkbox))



    def on_object_selected(self, *args):
        """Callback when objects are selected in the list."""
        selected = cmds.textScrollList(self.object_list, query=True, selectItem=True)
        if selected:
            cmds.select(selected, replace=True)

    def add_selected(self, *args):
        """Add currently selected objects to the list."""
        selection = cmds.ls(selection=True, type='transform')
        if not selection:
            cmds.warning("No transform objects selected.")
            return

        added_count = 0
        for obj in selection:
            if obj not in self.selected_objects:
                self.selected_objects.append(obj)
                cmds.textScrollList(self.object_list, edit=True, append=obj)
                added_count += 1



    def remove_selected(self, *args):
        """Remove selected objects from the list."""
        selected = cmds.textScrollList(self.object_list, query=True, selectItem=True)
        if not selected:
            cmds.warning("No objects selected in the list.")
            return

        for obj in selected:
            if obj in self.selected_objects:
                self.selected_objects.remove(obj)
                cmds.textScrollList(self.object_list, edit=True, removeItem=obj)



    def clear_all(self, *args):
        """Clear all objects from the list."""
        self.selected_objects.clear()
        cmds.textScrollList(self.object_list, edit=True, removeAll=True)




    def validate_inputs(self):
        """Validate user inputs before processing."""
        if not self.selected_objects:
            cmds.warning("No objects selected for group insertion.")
            return False

        # Check if objects still exist
        valid_objects = []
        for obj in self.selected_objects:
            if cmds.objExists(obj):
                valid_objects.append(obj)
            else:
                cmds.warning(f"Object '{obj}' no longer exists and will be skipped.")

        self.selected_objects = valid_objects
        if not valid_objects:
            cmds.warning("No valid objects remaining.")
            return False

        group_data = [(cmds.textField(field, query=True, text=True), 
                       cmds.checkBox(checkbox, query=True, value=True)) 
                      for field, checkbox in self.group_fields]
        group_data = [(name.strip(), pivot) for name, pivot in group_data if name.strip()]

        if not group_data:
            cmds.warning("No group names specified.")
            return False

        return group_data

    def insert_groups(self, *args):
        """Main function to insert groups between objects and their parents."""
        group_data = self.validate_inputs()
        if not group_data:
            return

        # Get naming options
        naming_based = cmds.radioButtonGrp(self.naming_radio, query=True, select=True)
        naming_style = cmds.radioButtonGrp(self.style_radio, query=True, select=True)

        # Enable undo for the operation
        cmds.undoInfo(openChunk=True)

        try:
            processed_objects = []
            
            for obj in self.selected_objects:
                if not cmds.objExists(obj):
                    continue

                # Store original hierarchy
                parent = cmds.listRelatives(obj, parent=True)
                children = cmds.listRelatives(obj, children=True, type='transform') or []

                # Get base name for naming
                base_name = obj
                if naming_based == 2:  # Upper Group
                    base_name = parent[0] if parent else obj
                elif naming_based == 3:  # Lower Group
                    base_name = obj

                # Create groups
                last_group = obj
                for group_name, object_based_pivot in group_data:
                    # Generate group name based on naming options
                    if naming_based == 1:  # Custom Name
                        final_group_name = group_name
                    else:  # Upper or Lower Group based
                        if naming_style == 1:  # Prefix
                            final_group_name = f"{group_name}_{base_name}"
                        else:  # Suffix
                            final_group_name = f"{base_name}_{group_name}"
                    
                    # Ensure unique group name
                    unique_name = cmds.ls(final_group_name, long=True)
                    if unique_name:
                        final_group_name = f"{final_group_name}_1"
                    
                    new_group = cmds.group(empty=True, name=final_group_name)
                    if object_based_pivot:
                        cmds.matchTransform(new_group, obj)
                    else:
                        cmds.xform(new_group, worldSpace=True, 
                                  translation=(0, 0, 0), rotation=(0, 0, 0), scale=(1, 1, 1))
                    
                    cmds.parent(last_group, new_group)
                    last_group = new_group

                # Reparent to maintain hierarchy
                if parent:
                    cmds.parent(last_group, parent[0])

                # Reparent children back to original object
                for child in children:
                    cmds.parent(child, obj)

                # Rename original object
                new_name = f"{obj}_GRP"
                cmds.rename(obj, new_name)
                processed_objects.append(new_name)

            # Select result
            if processed_objects:
                cmds.select(clear=True)
                for obj in processed_objects:
                    if cmds.objExists(obj):
                        cmds.select(obj, add=True)


            cmds.inViewMessage(assistMessage=f"Groups inserted successfully for {len(processed_objects)} object(s).", 
                             pos='midCenter', fade=True, fadeInTime=0.1, fadeOutTime=2.0)

        except Exception as e:
            cmds.error(f"Error during group insertion: {str(e)}")

        finally:
            cmds.undoInfo(closeChunk=True)


def create_tool():
    """Create and return the tool instance."""
    try:
        tool = InsertGroupTool()
        return tool
    except Exception as e:
        cmds.error(f"Failed to create Insert Group Tool: {str(e)}")
        return None


def show_ui():
    """Show the tool UI."""
    tool = create_tool()
    if tool:
        tool.create_ui()
    return tool


def close_ui():
    """Close the tool UI if it exists."""
    window_name = "InsertGroupTool"
    if cmds.window(window_name, exists=True):
        cmds.deleteUI(window_name)
        return True
    return False


def main():
    """Main function to create and show the tool."""
    return show_ui()


if __name__ == "__main__":
    main()