from __future__ import annotations

import json
import typing
from typing import Any

from overrides import override

from tp.core import log
from tp.common.qt import api as qt
from tp.common.nodegraph.core import factory, scene
from tp.common.nodegraph.models import graph as graph_model
from tp.common.nodegraph.graphics import view
from tp.common.nodegraph.widgets import palette, graph as graph_widget

if typing.TYPE_CHECKING:
    from tp.common.nodegraph.core.node import BaseNode


logger = log.rigLogger


class NodeGraph(qt.QObject):

    def __init__(
            self, model: graph_model.NodeGraphModel | None = None, viewer: view.GraphicsView | None = None,
            parent: qt.QObject | None = None):
        super().__init__(parent=parent)

        self.setObjectName('NodeGraph')

        self._model = model or graph_model.NodeGraphModel()
        self._scene = scene.Scene()
        self._viewer = viewer or view.GraphicsView(self._scene.graphics_scene)
        self._widget: graph_widget.NodeGraphWidget | None = None

        self._setup_signals()

        self._update_title()

    def __repr__(self) -> str:
        return '<{}("root") object at {}>'.format(self.__class__.__name__, hex(id(self)))

    @property
    def model(self) -> graph_model.NodeGraphModel:
        return self._model

    @property
    def scene(self) -> scene.Scene:
        return self._scene

    @property
    def file_name(self) -> str:
        return self.scene.file_name

    @property
    def file_base_name(self) -> str:
        name = self.scene.file_base_name
        return name or 'Untitled'

    @property
    def user_friendly_title(self) -> str:
        file_name = self.file_base_name
        if self.scene.has_been_modified:
            file_name += '*'

        return file_name

    # @override
    # def contextMenuEvent(self, event: qt.QContextMenuEvent) -> None:
    #
    #     def _handle_node_context_menu():
    #         context_menu = NodeContextMenu(self)
    #         context_menu.exec_(self.mapToGlobal(event.pos()))
    #
    #     def _handle_edge_context_menu():
    #         pass
    #
    #     if self._viewer.is_view_dragging:
    #         event.ignore()
    #         return
    #
    #     try:
    #         item = self.scene.item_at(event.pos())
    #         if not item:
    #             _handle_node_context_menu()
    #         if hasattr(item, 'node') or hasattr(item, 'socket') or not item:
    #             _handle_node_context_menu()
    #         elif hasattr(item, 'edge'):
    #             _handle_edge_context_menu()
    #         super().contextMenuEvent(event)
    #     except Exception:
    #         logger.exception('contextMenuEvent exception', exc_info=True)

    def node_by_id(self, node_id: str | None) -> BaseNode | None:
        """
        Returns the node from given node ID string.

        :param str node_id: ID of the node to retrieve.
        :return: node instance with given ID.
        :rtype: BaseNode or None
        """

        return self._model.nodes.get(node_id)

    def node_by_name(self, name: str) -> BaseNode | None:
        """
        Returns the node from given name.

        :param str name: name of the node to get.
        :return: node instance with given name.
        :rtype: BaseNode or None
        """

        found_node: BaseNode | None = None
        for node in self._model.nodes.values():
            if node.name() == name:
                found_node = node
                break

        return found_node

    def create_node(
            self, node_type: int | str, name: str | None = None, selected: bool = True,
            color: tuple[int, int, int] | str | None = None, text_color: tuple[int, int, int] | str | None = None,
            header_color: tuple[int, int, int] | str | None = None, pos: list[int, int] | None = None,
            push_undo: bool = True) -> BaseNode:
        """
        Creates a new node in the node graph.

        :param int or str node_type: node instance type.
        :param str name: name of the node.
        :param bool selected: whether created node should be set as selected.
        :param tuple[int, int, int] or str or None color: optional node color.
        :param tuple[int, int, int] or str or None text_color: optional node text color.
        :param tuple[int, int, int] or str or None header_color: optional node header color.
        :param list[int, int] pos: optional node position within scene.
        :param bool push_undo: whether command should be registered within undo stack.
        :return: newly created node instance.
        :rtype: BaseNode
        """

        new_node = factory.create_node(node_type)

    def widget(self) -> graph_widget.NodeGraphWidget:
        """
        Returns graph widget for adding graph into a layout.

        :return: node graph widget.
        :rtype: graph_widget.NodeGraphWidget
        """

        if self._widget is not None:
            return self._widget

        self._widget = graph_widget.NodeGraphWidget()
        self._widget.addTab(self._viewer, 'Node Graph')
        tab_bar = self._widget.tabBar()
        for btn_flag in [tab_bar.RightSide, tab_bar.LeftSide]:
            tab_btn = tab_bar.tabButton(0, btn_flag)
            if not tab_btn:
                continue
            tab_btn.deleteLater()
            tab_bar.setTabButton(0, btn_flag, None)
        self._widget.tabCloseRequested.connect(self._on_close_sub_graph_tab)

        self._setup_actions(self._widget)

        return self._widget

    def is_modified(self) -> bool:
        """
        Returns whether editor scene has been modified by user.

        :return: True if scene has been modified; False otherwise.
        :rtype: bool
        """

        return self.scene.has_been_modified

    def maybe_save(self) -> bool:
        """
        Shows a warning message if save is modified and not saved.

        :return: True is scene was saved or has  not been modified; False otherwise.
        :rtype: bool
        """

        if not self.is_modified():
            return True

        res = qt.QMessageBox.warning(
            self.widget(), 'Build not saved', 'Save Changes to current build?',
            qt.QMessageBox.Save | qt.QMessageBox.No | qt.QMessageBox.Cancel)
        if res == qt.QMessageBox.Save:
            return self.save_build()
        elif res == qt.QMessageBox.No:
            return True
        elif res == qt.QMessageBox.Cancel:
            return False

        return True

    def save_build_as(self) -> bool:
        """
        Saves current graph into disk in a new file.

        :return: True if save operation was successful; False otherwise.
        :rtype: bool
        """

        graph_filter = 'Graph (*.graph)'
        file_path = qt.QFileDialog.getSaveFileName(self.widget(), 'Save graph to file', '', graph_filter)[0]
        if not file_path:
            return False

        self.scene.save_to_file(file_path)

        return True

    def open_build(self) -> bool:
        """
        Opens a graph.

        :return: True if build was opened successfully; False otherwise.
        :rtype: bool
        """

        if not self.maybe_save():
            return False

        graph_filter = 'Graph (*.graph)'
        file_path = qt.QFileDialog.getOpenFileName(self.widget(), 'Open graph', '', graph_filter)[0]
        if not file_path:
            return False

        self.scene.load_from_file(file_path)

        return True

    def new_build(self):
        """
        Clears current scene and shows a warning message if current build has not been modified.
        """

        if not self.maybe_save():
            return

        self.scene.clear()
        self.scene.file_name = None

    def save_build(self):
        """
        Saves current build graph into disk.

        :return: True if save operation was successful; False otherwise.
        :rtype: bool
        """

        res = True
        if self.scene.file_name:
            self.scene.save_to_file(self.scene.file_name)
        else:
            res = self.save_build_as()

        return res

    def _setup_actions(self, widget: graph_widget.NodeGraphWidget):
        """
        Internal function that setup all actions.
        """

        widget.addAction(palette.PopupNodesPalette.show_action(self, self._viewer))

    def _setup_signals(self):
        """
        Internal function that creates all signal connections.
        """

        self.scene.signals.itemDragEntered.connect(self._on_item_drag_enter)
        self.scene.signals.itemDropped.connect(self._on_item_dropped)
        self.scene.signals.fileNameChanged.connect(self._update_title)
        self.scene.signals.modified.connect(self._update_title)

        self._viewer.nodeBackdropUpdated.connect(self._on_node_backdrop_updated)

    def _update_title(self):
        """
        Internal function that updates editor title.
        """

        pass

        # self.setWindowTitle(self.user_friendly_title)

    def _on_item_drag_enter(self, event: qt.QDragEnterEvent):
        """
        Internal callback function that is called each time an item is dragged within editor scene view.

        :param qt.QDragEnterEvent event: Qt drag enter event.
        """

        logger.debug('On item drag enter')
        if event.mimeData().hasFormat('noddle/x-node-palette_item') or event.mimeData().hasFormat('noddle/x-vars_item'):
            event.acceptProposedAction()
        else:
            logger.warning(f'Unsupported item: {event.mimeData().formats()}')
            event.setAccepted(False)

    def _on_item_dropped(self, event: qt.QDropEvent):
        """
        Internal callback function that is called each time an item is dropped within editor scene view.

        :param qt.QDropEvent event: Qt drop event.
        """

        def _handle_nodes_palette_drop():
            event_data = event.mimeData().data('noddle/x-node-palette_item')
            data_stream = qt.QDataStream(event_data, qt.QIODevice.ReadOnly)
            pixmap = qt.QPixmap()
            data_stream >> pixmap
            node_id = data_stream.readInt32()
            json_data = json.loads(data_stream.readQString())
            mouse_pos = event.pos()
            scene_pos = self._scene.view.mapToScene(mouse_pos)
            logger.debug(f'''Dropped Item:
                            > NODE_ID: {node_id}
                            > DATA: {json_data}
                            > MOUSE POS: {mouse_pos}
                            > SCENE POS {scene_pos}''')
            self._scene.spawn_node_from_data(node_id, json_data, scene_pos)
            event.setDropAction(qt.Qt.MoveAction)
            event.accept()

        def _handle_variable_drop():
            event_data = event.mimeData().data('noddle/x-vars_item')
            data_stream = qt.QDataStream(event_data, qt.QIODevice.ReadOnly)
            json_data = json.loads(data_stream.readQString())
            mouse_pos = event.pos()
            scene_pos = self.scene.view.mapToScene(mouse_pos)
            logger.debug('''Dropped Varible:
                            > DATA: {data}
                            > SCENE POS {scene_pos}'''.format(data=json_data, scene_pos=scene_pos))
            var_name = json_data['var_name']
            get_set_menu = qt.QMenu(self.widget())
            getter_action = qt.QAction('Get', get_set_menu)
            setter_action = qt.QAction('Set', get_set_menu)
            get_set_menu.addAction(getter_action)
            get_set_menu.addAction(setter_action)
            result_action = get_set_menu.exec_(self.widget().mapToGlobal(event.pos()))
            if result_action is None:
                return
            self.scene.spawn_getset(var_name, scene_pos, setter=result_action == setter_action)
            event.setDropAction(qt.Qt.MoveAction)
            event.accept()

        logger.debug('On item drop')
        if event.mimeData().hasFormat('noddle/x-node-palette_item'):
            _handle_nodes_palette_drop()
        elif event.mimeData().hasFormat('noddle/x-vars_item'):
            _handle_variable_drop()
        else:
            logger.warning('Unsupported item format: {0}'.format(event.mimeData()))
            event.ignore()
            return

    def _on_node_backdrop_updated(self, node_id: str, update_property: str, value: Any):
        """
        Internal callback function that is called each time a backdrop node is updated.

        :param str node_id: backdrop node ID.
        :param str update_property: updated property.
        :param Any value: updated property value.
        """

        backdrop_node = self.node_by_id(node_id)
        # if backdrop_node and isinstance(backdrop_node, node_backdrop.BackdropNode):
        #     backdrop_node.update_property(update_property, value)

    def _on_close_sub_graph_tab(self, index: int):
        """
        Internal callback function that is called each time the close button is clickied on expanded sub graph tab.

        :param int index: tab index.
        """

        pass


class NodeContextMenu(qt.QMenu):
    def __init__(self, graph: NodeGraph):
        super().__init__('Node', graph)

        self._scene = graph.scene

        self._setup_actions()
        self._populate()
        self._setup_signals()

    def _setup_actions(self):
        """
        Internal function that setup menu actions.
        """

        self._copy_action = qt.QAction('&Copy', self)
        self._cut_action = qt.QAction('&Cut', self)
        self._paste_action = qt.QAction('&Paste', self)
        self._delete_action = qt.QAction('&Delete', self)

    def _populate(self):
        """
        Internal function that populates menu.
        """

        self.addAction(self._copy_action)
        self.addAction(self._cut_action)
        self.addAction(self._paste_action)
        self.addSeparator()
        self.addAction(self._delete_action)

    def _setup_signals(self):
        """
        Internal function that setup menu connections.
        """

        self._copy_action.triggered.connect(self._on_copy_action_triggered)
        self._cut_action.triggered.connect(self._on_cut_action_triggered)
        self._paste_action.triggered.connect(self._on_paste_action_triggered)
        self._delete_action.triggered.connect(self._on_delete_action_triggered)

    def _on_copy_action_triggered(self):
        """
        Internal callback funtion that is called each time Copy action is triggered by the user.
        """

        if not self._scene:
            return

        self._scene.copy_selected()

    def _on_cut_action_triggered(self):
        """
        Internal callback funtion that is called each time Cut action is triggered by the user.
        """

        if not self._scene:
            return

        self._scene.cut_selected()

    def _on_paste_action_triggered(self):
        """
        Internal callback funtion that is called each time Paste action is triggered by the user.
        """

        if not self._scene:
            return

        self._scene.paste_from_clipboard()

    def _on_delete_action_triggered(self):
        """
        Internal callback funtion that is called each time Delete action is triggered by the user.
        """

        if not self._scene:
            return

        self._scene.delete_selected()
