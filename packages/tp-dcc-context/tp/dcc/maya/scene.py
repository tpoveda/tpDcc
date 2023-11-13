from __future__ import annotations

import enum

from overrides import override

import maya.api.OpenMaya as OpenMaya

from tp.dcc.abstract import scene
from tp.maya.cmds import scene as cmds_scene
from tp.maya.om import dagpath


class FileExtensions(enum.IntEnum):
    """
    Enumerator that defines available file extensions for Maya
    """

    mb = 0
    ma = 1


class MayaScene(scene.AbstractScene):

    __slots__ = ()
    __extensions__ = FileExtensions

    @override
    def is_new_scene(self) -> bool:
        """
        Returns whether this is an untitled scene file.

        :return: True if scene is new; False otherwise.
        :rtype: bool
        """

        return cmds_scene.is_new_scene()

    @override
    def is_save_required(self) -> bool:
        """
        Returns whether the open scene file has changes that need to be saved.

        :return: True if scene has been modified; False otherwise.
        :rtype: bool
        """

        return cmds_scene.current_scene_is_modified()

    @override(check_signature=False)
    def active_selection(self) -> list[OpenMaya.MObject]:
        """
        Returns current active selection.

        :return: list of active nodes.
        :rtype: list[OpenMaya.MObject]
        """

        selection = OpenMaya.MGlobal.getActiveSelectionList()       # type: OpenMaya.MSelectionList
        return [selection.getDependNode(i) for i in range(selection.length())]

    @override(check_signature=False)
    def set_active_selection(self, selection: list[OpenMaya.MObject], replace: bool = True):
        """
         Updates active selection.

         :param list[OpenMaya.MObject] selection: list of nodes to set as the active ones.
         :param bool replace: whether to replace selection or add to current one.
         """

        if not replace:
            selection.extend(self.active_selection())

        selection_list = dagpath.create_selection_list(selection)
        OpenMaya.MGlobal.setActiveSelectionList(selection_list)

    @override
    def clear_active_selection(self):
        """
        Clears current active selection.
        """

        OpenMaya.MGlobal.clearSelectionList()
