from collections import namedtuple
from enum import Enum
from random import uniform, choices
from utils import CONFIG, attraction_to_radius, attraction_decay, Action, ActionType, ContextRequest, Point, ModifierType
import numpy as np
from copy import deepcopy

class CellStatus(Enum):
    DEAD = 0
    ALIVE = 1


class Cell:
    def __init__(self, id=-1, p_migrate=0, p_prolif=0, attraction_generated=0):
        self.id = id
        self.attraction_generated = attraction_generated
        self.p_migrate = p_migrate
        self.p_prolif = p_prolif
        self.attraction_matrix = self.init_attraction_matrix()

    def get_actions(self, grid_context: dict):
        return []

    def get_context(self):
        return []

    def is_alive(self):
        return self.status == CellStatus.ALIVE

    def get_modifiers(self):
        return {ModifierType.ATTRACTION_MATRIX : self.attraction_matrix}

    def choose_direction(self, grid_context) -> Point:
        direction = Point(0, 0)  # Default is no movement

        attractions = grid_context[ContextRequest.ATTRACTION_IN_NEIGHBORHOOD]
        
        attraction_sum = sum(attractions.values())
        if (attraction_sum):  # If there is attraction
            direction = choices(list(attractions.keys()), [
                                val**10/attraction_sum**10 for val in attractions.values()])[0]
        if(type(self) == TipCell and attraction_sum):
            new_attr = deepcopy(attractions)
            for attr in new_attr:
                new_attr[attr] = round(new_attr[attr]**10/attraction_sum**10,3)
            print(f"Cell: {self.id}, decision: {direction},{round(attractions[direction]**10/attraction_sum**10, 3)} out of {new_attr}, \n total {attractions} \n")
        return direction

    def generate_actions_by_attraction(self, grid_context, cond : bool, action_type: ActionType):
        actions = []
        if (cond):
            direction = self.choose_direction(grid_context)
            if (direction != Point(0, 0)):
                actions.append(Action(dst=direction, type=action_type))
        return actions

    def init_attraction_matrix(self):
        radius = attraction_to_radius(self.attraction_generated)
        center = Point(radius, radius)
        print(f"{radius}")
        mat = np.zeros(shape=((2*radius)+1, (2*radius)+1), dtype=float)  #! 2*radius+1 because we want the center to be the cell itself
        for (x,y), attraction in np.ndenumerate(mat):
                mat[x][y] = attraction_decay(self.attraction_generated, Point(x,y).dist(center)) 
        return mat


class TipCell(Cell):
    def __init__(self, id, p_migrate=CONFIG["defaults"]["tip_cell"]["p_migrate"], attraction_generated=CONFIG["defaults"]["tip_cell"]["attraction_generated"]):
        Cell.__init__(self, id=id, p_migrate=p_migrate,
                      attraction_generated=attraction_generated)

    def get_actions(self, grid_context):
        return self.generate_actions_by_attraction(grid_context=grid_context, cond=self.should_migrate(), action_type=ActionType.MIGRATE)

    def get_context(self):
        return [ContextRequest.ATTRACTION_IN_NEIGHBORHOOD]
    
    def should_migrate(self):
        return (uniform(0, 1) < self.p_migrate)


class StalkCell(Cell):
    def __init__(self, p_prolif=CONFIG["defaults"]["stalk_cell"]["p_prolif"], p_branch=CONFIG["defaults"]["stalk_cell"]["p_branch"]):
        Cell.__init__(self, p_prolif=p_prolif)
        self.p_branch = p_branch
        self.count_prolif = 0

    def get_context(self):
        return [ContextRequest.ATTRACTION_IN_NEIGHBORHOOD, ContextRequest.NUM_NEIGHBORS]

    def get_actions(self, grid_context):
        return self.generate_actions_by_attraction(grid_context, self.should_prolif(grid_context), ActionType.PROLIF)

    def should_prolif(self, grid_context):
        num_neighbors = grid_context[ContextRequest.NUM_NEIGHBORS]
        cond_p_prolif = uniform(0, 1) < self.p_prolif * (1/((num_neighbors**2)+1))
        cond_max_prolif = self.count_prolif < CONFIG["defaults"]["stalk_cell"]["max_prolif_times"]
        cond_combined = cond_max_prolif and cond_p_prolif
        if cond_combined:
            self.count_prolif += 1
        return cond_combined

class AttractorCell(Cell):
    def __init__(self, p_migrate=CONFIG["defaults"]["attractor_cell"]["p_migrate"], attraction_generated=CONFIG["defaults"]["attractor_cell"]["attraction_generated"]):
        Cell.__init__(self, p_migrate=p_migrate,
                      attraction_generated=attraction_generated)
