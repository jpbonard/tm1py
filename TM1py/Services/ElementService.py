# -*- coding: utf-8 -*-
import json
from typing import List, Union, Iterable, Optional

from requests import Response

from TM1py.Objects import ElementAttribute, Element
from TM1py.Services.ObjectService import ObjectService
from TM1py.Services.RestService import RestService
from TM1py.Utils import CaseAndSpaceInsensitiveDict, format_url, CaseAndSpaceInsensitiveSet
from TM1py.Utils import build_element_unique_names, CaseAndSpaceInsensitiveTuplesDict


class ElementService(ObjectService):
    """ Service to handle Object Updates for TM1 Dimension (resp. Hierarchy) Elements

    """

    def __init__(self, rest: RestService):
        super().__init__(rest)

    def get(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Element:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$expand=*",
            dimension_name, hierarchy_name, element_name)
        response = self._rest.GET(url, **kwargs)
        return Element.from_dict(response.json())

    def create(self, dimension_name: str, hierarchy_name: str, element: Element, **kwargs) -> Response:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements",
            dimension_name,
            hierarchy_name)
        return self._rest.POST(url, element.body, **kwargs)

    def update(self, dimension_name: str, hierarchy_name: str, element: Element, **kwargs) -> Response:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element.name)
        return self._rest.PATCH(url, element.body, **kwargs)

    def exists(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> bool:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._exists(url, **kwargs)

    def delete(self, dimension_name: str, hierarchy_name: str, element_name: str, **kwargs) -> Response:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_name)
        return self._rest.DELETE(url, **kwargs)

    def get_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[Element]:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$expand=*&$filter=Type ne 3",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [Element.from_dict(element) for element in response.json()["value"]]

    def get_leaf_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        url = format_url("/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name&$filter=Type ne 3",
                         dimension_name,
                         hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_element_names(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        """ Get all elementnames

        :param dimension_name:
        :param hierarchy_name:
        :return: Generator of element-names
        """
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return [e["Name"] for e in response.json()['value']]

    def get_number_of_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?&$count&$top=0",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.json()["@odata.count"])

    def get_number_of_consolidated_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$filter=Type eq 3&$count&$top=0",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.json()["@odata.count"])

    def get_number_of_leaf_elements(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$filter=Type ne 3&$count&$top=0",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.json()["@odata.count"])

    def get_all_leaf_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                         **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values for leaf elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        mdx_elements = f"{{ Tm1FilterByLevel ( {{ Tm1SubsetAll ([{dimension_name}].[{hierarchy_name}]) }} , 0 ) }}"
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements, **kwargs)

    def get_all_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                    **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """

        mdx_elements = f"{{ Tm1SubsetAll ([{dimension_name}].[{hierarchy_name}]) }}"
        return self.get_element_identifiers(dimension_name, hierarchy_name, mdx_elements, **kwargs)

    def get_element_identifiers(self, dimension_name: str, hierarchy_name: str,
                                elements: Union[str, List[str]], **kwargs) -> CaseAndSpaceInsensitiveSet:
        """ Get all element names and alias values for a set of elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param elements: MDX (Set) expression or iterable of elements
        :return:
        """

        alias_attributes = self.get_alias_element_attributes(dimension_name, hierarchy_name, **kwargs)

        if isinstance(elements, str):
            mdx_element_selection = elements
        else:
            mdx_element_selection = ",".join(build_element_unique_names(
                [dimension_name] * len(elements),
                elements,
                [hierarchy_name] * len(elements)))
        mdx = """
             SELECT
             {{ {elem_mdx} }} ON ROWS, 
             {{ {attr_mdx} }} ON COLUMNS
             FROM [}}ElementAttributes_{dim}]
             """.format(
            elem_mdx=mdx_element_selection,
            attr_mdx=",".join(build_element_unique_names(
                ["}ElementAttributes_" + dimension_name] * len(alias_attributes), alias_attributes)),
            dim=dimension_name)
        return self._retrieve_mdx_rows_and_cell_values_as_string_set(mdx, **kwargs)

    def get_attribute_of_elements(self, dimension_name: str, hierarchy_name: str, attribute: str,
                                  elements: Union[str, List[str]] = None, exclude_empty_cells: bool = True,
                                  element_unique_names: bool = False) -> dict:
        """
         Get element name and attribute value for a set of elements in a hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :param attribute: Name of the Attribute
        :param elements:  MDX (Set) expression or iterable of elements
        :param exclude_empty_cells: Boolean
        :param element_unique_names: Boolean
        :return: Dict {'01':'Jan', '02':'Feb'}
        """
        if not elements:
            elements = self.get_element_names(dimension_name=dimension_name, hierarchy_name=hierarchy_name)

        if isinstance(elements, str):
            mdx_element_selection = elements
        else:
            mdx_element_selection = ",".join(build_element_unique_names(
                [dimension_name] * len(elements),
                elements,
                [hierarchy_name] * len(elements)))
        mdx = """
             SELECT
             {{ {elem_mdx} }} ON ROWS, 
             {{ {attr_mdx} }} ON COLUMNS
             FROM [}}ElementAttributes_{dim}]
             """.format(
            elem_mdx=mdx_element_selection,
            attr_mdx="[}ElementAttributes_" + dimension_name + "].[" + attribute + "]",
            dim=dimension_name)
        rows_and_values = self._retrieve_mdx_rows_and_values(mdx, element_unique_names=element_unique_names)
        return self._extract_dict_from_rows_and_values(rows_and_values, exclude_empty_cells=exclude_empty_cells)

    @staticmethod
    def _extract_dict_from_rows_and_values(
            rows_and_values: CaseAndSpaceInsensitiveTuplesDict,
            exclude_empty_cells: bool = True) -> dict:
        """ Helper function for get_element_by_attribute method

        :param rows_and_values:
        :param exclude_empty_cells: Boolean
        :return: Dictionary of Element:Attribute_Value
        """
        result_set = dict()
        for row_elements, cell_values in rows_and_values.items():
            for row_element in row_elements:
                for cell_value in cell_values:
                    if isinstance(cell_value, str):
                        if cell_value or not exclude_empty_cells:
                            result_set[row_element] = cell_value
        return result_set

    def get_level_names(self, dimension_name: str, hierarchy_name: str, descending: bool = True, **kwargs) -> List[str]:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Levels?$select=Name",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        if descending:
            return [level["Name"] for level in reversed(response.json()["value"])]
        else:
            return [level["Name"] for level in response.json()["value"]]

    def get_levels_count(self, dimension_name: str, hierarchy_name: str, **kwargs) -> int:
        url = format_url("/api/v1/Dimensions('{}')/Hierarchies('{}')/Levels/$count", dimension_name, hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        return int(response.text)

    def get_element_types(self, dimension_name: str, hierarchy_name: str,
                          skip_consolidations: bool = False, **kwargs) -> CaseAndSpaceInsensitiveDict:
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements?$select=Name,Type{}",
            dimension_name,
            hierarchy_name,
            "&$filter=Type ne 3" if skip_consolidations else "")
        response = self._rest.GET(url, **kwargs)

        result = CaseAndSpaceInsensitiveDict()
        for element in response.json()["value"]:
            result[element['Name']] = element["Type"]
        return result

    def attribute_cube_exists(self, dimension_name: str, **kwargs) -> bool:
        url = format_url("/api/v1/Cubes('{}')", self.ELEMENT_ATTRIBUTES_PREFIX + dimension_name)
        return self._exists(url, **kwargs)

    def _retrieve_mdx_rows_and_cell_values_as_string_set(self, mdx: str, exclude_empty_cells=True, **kwargs):
        from TM1py import CellService
        return CellService(self._rest).execute_mdx_rows_and_values_string_set(mdx, exclude_empty_cells, **kwargs)

    def _retrieve_mdx_rows_and_values(self, mdx: str, **kwargs):
        from TM1py import CellService
        return CellService(self._rest).execute_mdx_rows_and_values(mdx, **kwargs)

    def get_alias_element_attributes(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[str]:
        """

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        attributes = self.get_element_attributes(dimension_name, hierarchy_name, **kwargs)
        return [attr.name
                for attr
                in attributes if attr.attribute_type == 'Alias']

    def get_element_attributes(self, dimension_name: str, hierarchy_name: str, **kwargs) -> List[ElementAttribute]:
        """ Get element attributes from hierarchy

        :param dimension_name:
        :param hierarchy_name:
        :return:
        """
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/ElementAttributes",
            dimension_name,
            hierarchy_name)
        response = self._rest.GET(url, **kwargs)
        element_attributes = [ElementAttribute.from_dict(ea) for ea in response.json()['value']]
        return element_attributes

    def get_elements_filtered_by_attribute(self, dimension_name: str, hierarchy_name: str, attribute_name: str,
                                           attribute_value: Union[str, float], **kwargs) -> List[str]:
        """ Get all elements from a hierarchy with given attribute value

        :param dimension_name:
        :param hierarchy_name:
        :param attribute_name:
        :param attribute_value:
        :return: List of element names
        """
        attribute_name = attribute_name.replace(" ", "")
        if isinstance(attribute_value, str):
            url = format_url("/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = "
                             "Attributes/{} eq '{}';$select=Name)",
                             dimension_name, hierarchy_name, attribute_name, attribute_value)

        else:
            url = format_url("/api/v1/Dimensions('{}')/Hierarchies('{}')?$expand=Elements($filter = "
                             "Attributes/{} eq {};$select=Name)",
                             dimension_name, hierarchy_name, attribute_name, attribute_value)

        response = self._rest.GET(url, **kwargs)
        return [elem['Name'] for elem in response.json()['Elements']]

    def create_element_attribute(self, dimension_name: str, hierarchy_name: str, element_attribute: ElementAttribute,
                                 **kwargs) -> Response:
        """ like AttrInsert

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        url = format_url(
            "/api/v1/Dimensions('{}')/Hierarchies('{}')/ElementAttributes",
            dimension_name,
            hierarchy_name)
        return self._rest.POST(url, element_attribute.body, **kwargs)

    def delete_element_attribute(self, dimension_name: str, hierarchy_name: str, element_attribute: str,
                                 **kwargs) -> Response:
        """ like AttrDelete

        :param dimension_name:
        :param hierarchy_name:
        :param element_attribute: instance of TM1py.ElementAttribute
        :return:
        """
        url = format_url(
            "/api/v1/Dimensions('}}ElementAttributes_{}')/Hierarchies('}}ElementAttributes_{}')/Elements('{}')",
            dimension_name,
            hierarchy_name,
            element_attribute)
        return self._rest.DELETE(url, **kwargs)

    def get_leaves_under_consolidation(self, dimension_name: str, hierarchy_name: str, consolidation: str,
                                       max_depth: int = None, **kwargs) -> List[str]:
        """ Get all leaves under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :return: 
        """
        return self.get_members_under_consolidation(dimension_name, hierarchy_name, consolidation, max_depth, True,
                                                    **kwargs)

    def get_members_under_consolidation(self, dimension_name: str, hierarchy_name: str, consolidation: str,
                                        max_depth: int = None, leaves_only: bool = False, **kwargs) -> List[str]:
        """ Get all members under a consolidated element

        :param dimension_name: name of dimension
        :param hierarchy_name: name of hierarchy
        :param consolidation: name of consolidated Element
        :param max_depth: 99 if not passed
        :param leaves_only: Only Leaf Elements or all Elements
        :return:
        """
        depth = max_depth if max_depth else 99
        # members to return
        members = []
        # build url
        bare_url = "/api/v1/Dimensions('{}')/Hierarchies('{}')/Elements('{}')?$select=Name,Type&$expand=Components("
        url = format_url(bare_url, dimension_name, hierarchy_name, consolidation)
        for _ in range(depth):
            url += "$select=Name,Type;$expand=Components("
        url = url[:-1] + ")" * depth

        response = self._rest.GET(url, **kwargs)
        consolidation_tree = response.json()

        # recursive function to parse consolidation_tree
        def get_members(element):
            if element["Type"] == "Numeric":
                members.append(element["Name"])
            elif element["Type"] == "Consolidated":
                if "Components" in element:
                    for component in element["Components"]:
                        if not leaves_only:
                            members.append(component["Name"])
                        get_members(component)

        get_members(consolidation_tree)
        return members

    def execute_set_mdx(
            self,
            mdx: str,
            top_records: Optional[int] = None,
            member_properties: Optional[Iterable[str]] = ('Name', 'Weight'),
            parent_properties: Optional[Iterable[str]] = ('Name', 'UniqueName'),
            element_properties: Optional[Iterable[str]] = ('Type', 'Level'),
            **kwargs) -> List:
        """
        :method to execute an MDX statement against a dimension
        :param mdx: valid dimension mdx statement
        :param top_records: number of records to return, default: all elements no limit
        :param member_properties: list of member properties to return, will always return name
        :param parent_properties: list of parent properties to return, can be empty
        :param element_properties: list of element properties to return, can be empty
        :return: dictionary of members, unique names, weights, types, and parents
        """

        top = f"$top={top_records};" if top_records else ""

        if not member_properties:
            member_properties = ['Name']

        member_properties = ",".join(member_properties)
        select_member_properties = f'$select={member_properties}'

        properties_to_expand = []
        if parent_properties:
            parent_properties = ",".join(parent_properties)
            select_parent_properties = f'Parent($select={parent_properties})'
            properties_to_expand.append(select_parent_properties)

        if element_properties:
            element_properties = ",".join(element_properties)
            select_element_properties = f'Element($select={element_properties})'
            properties_to_expand.append(select_element_properties)

        if properties_to_expand:
            expand_properties = f';$expand={",".join(properties_to_expand)}'
        else:
            expand_properties = ""

        url = f'/api/v1/ExecuteMDXSetExpression?$expand=Tuples({top}' \
              f'$expand=Members({select_member_properties}' \
              f'{expand_properties}))'

        payload = {"MDX": mdx}
        response = self._rest.POST(url, json.dumps(payload, ensure_ascii=False), **kwargs)
        raw_dict = response.json()
        return [tuples['Members'] for tuples in raw_dict['Tuples']]
