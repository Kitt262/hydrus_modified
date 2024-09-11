import os
import typing

from qtpy import QtCore as QC
from qtpy import QtWidgets as QW

from hydrus.core import HydrusConstants as HC
from hydrus.core import HydrusExceptions

from hydrus.client import ClientConstants as CC
from hydrus.client import ClientGlobals as CG
from hydrus.client.gui import ClientGUICore as CGC
from hydrus.client.gui import ClientGUIDialogsMessage
from hydrus.client.gui import ClientGUIFunctions
from hydrus.client.gui import ClientGUIMenus
from hydrus.client.gui import ClientGUIShortcuts
from hydrus.client.gui import QtPorting as QP
from hydrus.client.gui.panels import ClientGUIScrolledPanels
from hydrus.client.gui.search import ClientGUIPredicatesMultiple
from hydrus.client.gui.search import ClientGUIPredicatesSingle
from hydrus.client.gui.search import ClientGUIPredicatesOR
from hydrus.client.gui.widgets import ClientGUICommon
from hydrus.client.search import ClientSearch

FLESH_OUT_SYSTEM_PRED_TYPES = {
    ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES,
    ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_AGE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HASH,
    ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_MIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_RATING,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA,
    ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE,
    ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER,
    ClientSearch.PREDICATE_TYPE_SYSTEM_URLS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS,
    ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES,
    ClientSearch.PREDICATE_TYPE_SYSTEM_TIME,
    ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS
}

def EditPredicates( widget: QW.QWidget, predicates: typing.Collection[ ClientSearch.Predicate ], empty_file_search_context: typing.Optional[ ClientSearch.FileSearchContext ] = None ) -> typing.List[ ClientSearch.Predicate ]:
    
    ( editable_predicates, only_invertible_predicates, non_editable_predicates ) = GetEditablePredicates( predicates )
    
    window = widget.window()
    
    from hydrus.client.gui import ClientGUITopLevelWindowsPanels
    
    if len( editable_predicates ) == 0 and len( only_invertible_predicates ) == 1:
        
        result = list( non_editable_predicates )
        result.append( only_invertible_predicates[0].GetInverseCopy() )
        
        return result
        
    elif len( editable_predicates ) > 0 or len( only_invertible_predicates ) > 0:
        
        title = 'edit predicates'
        
        if len( editable_predicates ) == 1:
            
            if list( editable_predicates )[0].GetType() == ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
                
                title = 'edit OR predicate'
                
            
        
        with ClientGUITopLevelWindowsPanels.DialogEdit( window, title ) as dlg:
            
            panel = EditPredicatesPanel( dlg, predicates, empty_file_search_context = empty_file_search_context )
            
            dlg.SetPanel( panel )
            
            if dlg.exec() == QW.QDialog.Accepted:
                
                edited_predicates = panel.GetValue()
                
                CG.client_controller.new_options.PushRecentPredicates( edited_predicates )
                
                result = list( non_editable_predicates )
                result.extend( edited_predicates )
                
                return result
                
            
        
    
    raise HydrusExceptions.CancelledException()
    
def FilterAndConvertLabelPredicates( predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.List[ ClientSearch.Predicate ]:
    
    good_predicates = []
    
    for predicate in predicates:
        
        predicate = predicate.GetCountlessCopy()
        
        predicate_type = predicate.GetType()
        
        if predicate_type in ( ClientSearch.PREDICATE_TYPE_LABEL, ClientSearch.PREDICATE_TYPE_PARENT ):
            
            continue
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_UNTAGGED:
            
            predicate = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '=', 0 ) )
            
        
        good_predicates.append( predicate )
        
    
    return good_predicates
    
def FleshOutPredicates( widget: QW.QWidget, predicates: typing.Collection[ ClientSearch.Predicate ] ) -> typing.List[ ClientSearch.Predicate ]:
    
    window = None
    
    predicates = FilterAndConvertLabelPredicates( predicates )
    
    good_predicates = []
    
    for predicate in predicates:
        
        value = predicate.GetValue()
        predicate_type = predicate.GetType()
        
        if value is None and predicate_type in FLESH_OUT_SYSTEM_PRED_TYPES:
            
            if window is None:
                
                if QP.isValid( widget ):
                    
                    window = widget.window()
                    
                
            
            from hydrus.client.gui import ClientGUITopLevelWindowsPanels
            
            with ClientGUITopLevelWindowsPanels.DialogEdit( window, 'input predicate', hide_buttons = True ) as dlg:
                
                panel = FleshOutPredicatePanel( dlg, predicate )
                
                dlg.SetPanel( panel )
                
                if dlg.exec() == QW.QDialog.Accepted:
                    
                    preds = panel.GetValue()
                    
                    CG.client_controller.new_options.PushRecentPredicates( preds )
                    
                    good_predicates.extend( preds )
                    
                
            
        else:
            
            good_predicates.append( predicate )
            
        
    
    return good_predicates
    
def GetEditablePredicates( predicates: typing.Collection[ ClientSearch.Predicate ] ):
    
    editable_predicates = [ predicate for predicate in predicates if predicate.IsEditable() ]
    only_invertible_predicates = [ predicate for predicate in predicates if predicate.IsInvertible() and not predicate.IsEditable() ]
    non_editable_predicates = [ predicate for predicate in predicates if not predicate.IsInvertible() and not predicate.IsEditable() ]
    
    return ( editable_predicates, only_invertible_predicates, non_editable_predicates )
    

class EditPredicatesPanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, predicates: typing.Collection[ ClientSearch.Predicate ], empty_file_search_context: typing.Optional[ ClientSearch.FileSearchContext ] = None ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        predicates = list( predicates )
        
        predicates.sort( key = lambda p: p.ToString( with_count = False ) )
        
        self._uneditable_predicates = []
        
        self._invertible_pred_buttons = []
        self._editable_pred_panels = []
        
        rating_preds = []
        
        # I hate this pred comparison stuff, but let's hang in there until we split this stuff up by type mate
        # then we can just have a dict type->panel_class lookup or whatever
        # also it would be nice to have proper rating editing here, think about it
        
        AGE_DELTA_PRED = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '>', 'delta', ( 2000, 1, 1, 1 ) ) )
        LAST_VIEWED_DELTA_PRED = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME, ( '>', 'delta', ( 2000, 1, 1, 1 ) ) )
        ARCHIVED_DELTA_PRED = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME, ( '>', 'delta', ( 2000, 1, 1, 1 ) ) )
        MODIFIED_DELTA_PRED = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME, ( '>', 'delta', ( 2000, 1, 1, 1 ) ) )
        KNOWN_URL_EXACT = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'exact_match', '', '' ) )
        KNOWN_URL_DOMAIN = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'domain', '', '' ) )
        KNOWN_URL_REGEX = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS, ( True, 'regex', '', '' ) )
        FILE_VIEWS_PRED = ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS, ( 'views', ( 'media', ), '>', 0 ) )
        
        for predicate in predicates:
            
            predicate_type = predicate.GetType()
            
            if predicate_type == ClientSearch.PREDICATE_TYPE_OR_CONTAINER:
                
                self._editable_pred_panels.append( ClientGUIPredicatesOR.ORPredicateControl( self, predicate, empty_file_search_context = empty_file_search_context ) )
                
            elif predicate_type in ( ClientSearch.PREDICATE_TYPE_TAG, ClientSearch.PREDICATE_TYPE_NAMESPACE, ClientSearch.PREDICATE_TYPE_WILDCARD ):
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSimpleTagTypes( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_AGE:
                
                if predicate.IsUIEditable( AGE_DELTA_PRED ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemAgeDelta( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemAgeDate( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME:
                
                if predicate.IsUIEditable( LAST_VIEWED_DELTA_PRED ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemLastViewedDelta( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemLastViewedDate( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME:
                
                if predicate.IsUIEditable( ARCHIVED_DELTA_PRED ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDelta( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDate( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
                
                if predicate.IsUIEditable( MODIFIED_DELTA_PRED ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDelta( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDate( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemHeight( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemWidth( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemRatio( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumPixels( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemDuration( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemFramerate( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_FRAMES:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumFrames( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemFileService( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
                
                if predicate.IsUIEditable( KNOWN_URL_EXACT ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsExactURL( self, predicate ) )
                    
                elif predicate.IsUIEditable( KNOWN_URL_DOMAIN ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsDomain( self, predicate ) )
                    
                elif predicate.IsUIEditable( KNOWN_URL_REGEX ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsRegex( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsURLClass( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumURLs( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HASH:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemHash( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemLimit( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MIME:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemMime( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumTags( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumNotes( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemHasNoteName( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemNumWords( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_DATA:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemSimilarToData( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO_FILES:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemSimilarToFiles( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemSize( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemTagAsNumber( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_COUNT:
                
                self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemDuplicateRelationships( self, predicate ) )
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
                
                if predicate.IsUIEditable( FILE_VIEWS_PRED ):
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemFileViewingStatsViews( self, predicate ) )
                    
                else:
                    
                    self._editable_pred_panels.append( ClientGUIPredicatesSingle.PanelPredicateSystemFileViewingStatsViewtime( self, predicate ) )
                    
                
            elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_RATING:
                
                rating_preds.append( predicate )
                
            elif predicate.IsInvertible():
                
                self._invertible_pred_buttons.append( ClientGUIPredicatesSingle.InvertiblePredicateButton( self, predicate ) )
                
            else:
                
                self._uneditable_predicates.append( predicate )
                
            
        
        if len( rating_preds ) > 0:
            
            self._editable_pred_panels.append( ClientGUIPredicatesMultiple.PanelPredicateSystemRating( self, rating_preds ) )
            
        
        vbox = QP.VBoxLayout()
        
        for button in self._invertible_pred_buttons:
            
            QP.AddToLayout( vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        stretch_needed = True
        
        for panel in self._editable_pred_panels:
            
            if isinstance( panel, ( ClientGUIPredicatesOR.ORPredicateControl, ClientGUIPredicatesSingle.PanelPredicateSystemMime ) ):
                
                flags = CC.FLAGS_EXPAND_BOTH_WAYS
                
                stretch_needed = False
                
            else:
                
                flags = CC.FLAGS_EXPAND_PERPENDICULAR
                
            
            QP.AddToLayout( vbox, panel, flags )
            
        
        if stretch_needed:
            
            vbox.addStretch( 1 )
            
        
        self.widget().setLayout( vbox )
        
    
    def CheckValid( self ):
        
        for panel in self._editable_pred_panels:
            
            panel.CheckValid()
            
        
    
    def GetValue( self ):
        
        return_predicates = list( self._uneditable_predicates )
        
        for button in self._invertible_pred_buttons:
            
            return_predicates.append( button.GetPredicate() )
            
        
        for panel in self._editable_pred_panels:
            
            return_predicates.extend( panel.GetPredicates() )
            
        
        return return_predicates
        
    
class FleshOutPredicatePanel( ClientGUIScrolledPanels.EditPanel ):
    
    def __init__( self, parent, predicate: ClientSearch.Predicate ):
        
        ClientGUIScrolledPanels.EditPanel.__init__( self, parent )
        
        predicate_type = predicate.GetType()
        
        self._predicates = []
        
        label = None
        
        page_name = 'page'
        pages = []
        
        recent_predicate_types = [ predicate_type ]
        static_pred_buttons = []
        editable_pred_panels = []
        
        if predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_AGE:
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 1, 0 ) ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 7, 0 ) ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 1, 0, 0 ) ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemAgeDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemAgeDate, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDate, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDate, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_TIME:
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_AGE ]
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 1, 0 ) ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 0, 7, 0 ) ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_AGE, ( '<', 'delta', ( 0, 1, 0, 0 ) ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemAgeDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemAgeDate, predicate ) )
            
            pages.append( ( 'import', recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_MODIFIED_TIME ]
            static_pred_buttons = []
            editable_pred_panels = []
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemModifiedDate, predicate ) )
            
            pages.append( ( 'modified', recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_LAST_VIEWED_TIME ]
            static_pred_buttons = []
            editable_pred_panels = []
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemLastViewedDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemLastViewedDate, predicate ) )
            
            pages.append( ( 'last viewed', recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
            
            page_name = 'archived'
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_ARCHIVED_TIME ]
            static_pred_buttons = []
            editable_pred_panels = []
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDelta, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemArchivedDate, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_DIMENSIONS:
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_PIXELS ]
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 16, 9 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 9, 16 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 4, 3 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( '=', 1, 1 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( 'taller than', 1, 1 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_RATIO, ( 'wider than', 1, 1 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 1920 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 1080 ) ) ), forced_label = '1080p', show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 1280 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 720 ) ) ), forced_label = '720p', show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_WIDTH, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 3840 ) ), ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HEIGHT, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 2160 ) ) ), forced_label = '4k', show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemHeight, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemWidth, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemRatio, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumPixels, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION:
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_FRAMES ]
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ClientSearch.NumberTest.STATICCreateFromCharacters( '>', 0 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_DURATION, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 0 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 30 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FRAMERATE, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 60 ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemDuration, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemFramerate, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumFrames, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_SERVICE:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemFileService, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsExactURL, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsDomain, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsRegex, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsURLClass, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumURLs, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_URLS:
            
            label = 'Note that "number of urls" counts all URLs, regardless of how important.'
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_KNOWN_URLS ]
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsExactURL, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsDomain, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsRegex, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemKnownURLsURLClass, predicate ) )
            
            pages.append( ( 'known urls', recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
            
            page_name = 'number of urls'
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS ]
            static_pred_buttons = []
            editable_pred_panels = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientSearch.NumberTest.STATICCreateFromCharacters( '>', 0 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_URLS, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 0 ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumURLs, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_PROPERTIES:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_AUDIO, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_TRANSPARENCY, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_EXIF, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_HUMAN_READABLE_EMBEDDED_METADATA, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_ICC_PROFILE, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE:
            
            recent_predicate_types = []
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, True ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_FORCED_FILETYPE, False ), ), show_remove_button = False ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_HASH:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemHash, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT:
            
            label = 'system:limit clips a large search result down to the given number of files. It is very useful for processing in smaller batches.'
            label += '\n' * 2
            label += 'For all the simpler sorts (filesize, duration, etc...), it will select the n largest/smallest in the result set appropriate for that sort. For complicated sorts like tags, it will sample randomly.'
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 64 ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 256 ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_LIMIT, 1024 ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemLimit, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_MIME:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemMime, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS:
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '>', 0 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_TAGS, ( '*', '=', 0 ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumTags, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NOTES:
            
            recent_predicate_types = [ ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientSearch.PREDICATE_TYPE_SYSTEM_HAS_NOTE_NAME ]
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientSearch.NumberTest.STATICCreateFromCharacters( '>', 0 ) ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_NOTES, ClientSearch.NumberTest.STATICCreateFromCharacters( '=', 0 ) ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumNotes, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemHasNoteName, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_NUM_WORDS:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemNumWords, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_RATING:
            
            services_manager = CG.client_controller.services_manager
            
            ratings_services = services_manager.GetServices( HC.RATINGS_SERVICES )
            
            if len( ratings_services ) > 0:
                
                editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesMultiple.PanelPredicateSystemRating, ( predicate, ) ) )
                
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIMILAR_TO:
            
            recent_predicate_types = []
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemSimilarToData, predicate ) )
            
            pages.append( ( 'data', recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
            
            page_name = 'files'
            
            recent_predicate_types = []
            static_pred_buttons = []
            editable_pred_panels = []
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemSimilarToFiles, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_SIZE:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemSize, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_TAG_AS_NUMBER:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemTagAsNumber, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS:
            
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, False ), ), show_remove_button = False ) )
            static_pred_buttons.append( ClientGUIPredicatesSingle.StaticSystemPredicateButton( self, ( ClientSearch.Predicate( ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_RELATIONSHIPS_KING, True ), ), show_remove_button = False ) )
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemDuplicateRelationships, predicate ) )
            
        elif predicate_type == ClientSearch.PREDICATE_TYPE_SYSTEM_FILE_VIEWING_STATS:
            
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemFileViewingStatsViews, predicate ) )
            editable_pred_panels.append( self._PredOKPanel( self, ClientGUIPredicatesSingle.PanelPredicateSystemFileViewingStatsViewtime, predicate ) )
            
        
        pages.append( ( page_name, recent_predicate_types, static_pred_buttons, editable_pred_panels ) )
        
        vbox = QP.VBoxLayout()
        
        if label is not None:
            
            st = ClientGUICommon.BetterStaticText( self, label = label )
            
            st.setWordWrap( True )
            
            QP.AddToLayout( vbox, st, CC.FLAGS_EXPAND_PERPENDICULAR )
            
        
        page_parent = self
        
        if len( pages ) > 1:
            
            self._notebook = ClientGUICommon.BetterNotebook( self )
            
            QP.AddToLayout( vbox, self._notebook, CC.FLAGS_EXPAND_BOTH_WAYS )
            
            page_parent = self._notebook
            
        
        first_editable_pred_panel = None
        
        for ( i, ( page_name, recent_predicate_types, static_pred_buttons, editable_pred_panels ) ) in enumerate( pages ):
            
            page_panel = QW.QWidget( page_parent )
            
            page_vbox = QP.VBoxLayout()
            
            all_static_preds = set()
            
            for pred_button in static_pred_buttons:
                
                all_static_preds.update( pred_button.GetPredicates() )
                
            
            if len( recent_predicate_types ) > 0:
                
                recent_predicates = CG.client_controller.new_options.GetRecentPredicates( recent_predicate_types )
                
                recent_predicates = [ pred for pred in recent_predicates if pred not in all_static_preds ]
                
                if len( recent_predicates ) > 0:
                    
                    recent_predicates_box = ClientGUICommon.StaticBox( page_panel, 'recent' )
                    
                    for recent_predicate in recent_predicates:
                        
                        button = ClientGUIPredicatesSingle.StaticSystemPredicateButton( recent_predicates_box, ( recent_predicate, ) )
                        
                        button.predicatesChosen.connect( self.StaticButtonClicked )
                        button.predicatesRemoved.connect( self.StaticRemoveButtonClicked )
                        
                        recent_predicates_box.Add( button, CC.FLAGS_EXPAND_PERPENDICULAR )
                        
                    
                    QP.AddToLayout( page_vbox, recent_predicates_box, CC.FLAGS_EXPAND_PERPENDICULAR )
                    
                
            
            for button in static_pred_buttons:
                
                QP.AddToLayout( page_vbox, button, CC.FLAGS_EXPAND_PERPENDICULAR )
                
                button.predicatesChosen.connect( self.StaticButtonClicked )
                button.predicatesRemoved.connect( self.StaticRemoveButtonClicked )
                
            
            stretch_needed = True
            
            for panel in editable_pred_panels:
                
                if first_editable_pred_panel is None:
                    
                    first_editable_pred_panel = panel
                    
                
                if isinstance( panel, self._PredOKPanel ) and isinstance( panel.GetPredicatePanel(), ClientGUIPredicatesSingle.PanelPredicateSystemMime ):
                    
                    flags = CC.FLAGS_EXPAND_BOTH_WAYS
                    
                    stretch_needed = False
                    
                else:
                    
                    flags = CC.FLAGS_EXPAND_PERPENDICULAR
                    
                
                QP.AddToLayout( page_vbox, panel, flags )
                
            
            if stretch_needed:
                
                page_vbox.addStretch( 1 )
                
            
            page_panel.setLayout( page_vbox )
            
            if i == 0 and len( static_pred_buttons ) > 0 and len( editable_pred_panels ) == 0:
                
                ClientGUIFunctions.SetFocusLater( static_pred_buttons[0] )
                
            elif first_editable_pred_panel is not None:
                
                ClientGUIFunctions.SetFocusLater( first_editable_pred_panel )
                
            
            if len( pages ) > 1:
                
                self._notebook.addTab( page_panel, page_name )
                
            else:
                
                QP.AddToLayout( vbox, page_panel, CC.FLAGS_EXPAND_BOTH_WAYS )
                
            
        
        self.widget().setLayout( vbox )
        
    
    def GetValue( self ):
        
        return self._predicates
        
    
    def StaticButtonClicked( self, button: ClientGUIPredicatesSingle.StaticSystemPredicateButton ):
        
        predicates = button.GetPredicates()
        
        self.SubPanelOK( predicates )
        
    
    def StaticRemoveButtonClicked( self, button: ClientGUIPredicatesSingle.StaticSystemPredicateButton ):
        
        predicates = button.GetPredicates()
        
        for predicate in predicates:
            
            CG.client_controller.new_options.RemoveRecentPredicate( predicate )
            
        
        button.hide()
        
        recent_static_box = button.parentWidget()
        
        static_buttons = [ w for w in recent_static_box.children() if isinstance( w, ClientGUIPredicatesSingle.StaticSystemPredicateButton ) ]
        
        if True not in ( w.isVisible() for w in static_buttons ):
            
            recent_static_box.hide()
            
        
    
    def SubPanelOK( self, predicates ):
        
        self._predicates = predicates
        
        self.parentWidget().DoOK()
        
    
    class _PredOKPanel( QW.QWidget ):
        
        def __init__( self, parent, predicate_panel_class, predicate ):
            
            super().__init__( parent )
            
            self._defaults_button = ClientGUICommon.BetterBitmapButton( self, CC.global_pixmaps().star, self._DefaultsMenu )
            self._defaults_button.setToolTip( ClientGUIFunctions.WrapToolTip( 'Set a new default.' ) )
            
            self._predicate_panel = predicate_panel_class( self, predicate )
            self._parent = parent
            
            self._ok = QW.QPushButton( 'ok', self )
            self._ok.clicked.connect( self._DoOK )
            self._ok.setObjectName( 'HydrusAccept' )
            
            hbox = QP.HBoxLayout()
            
            QP.AddToLayout( hbox, self._defaults_button, CC.FLAGS_CENTER_PERPENDICULAR )
            QP.AddToLayout( hbox, self._predicate_panel, CC.FLAGS_EXPAND_SIZER_BOTH_WAYS )
            QP.AddToLayout( hbox, self._ok, CC.FLAGS_CENTER_PERPENDICULAR )
            
            self.setLayout( hbox )
            
            self.setFocusProxy( self._ok )
            
        
        def _DefaultsMenu( self ):
            
            menu = ClientGUIMenus.GenerateMenu( self )
            
            ClientGUIMenus.AppendMenuItem( menu, 'set this as new default', 'Set the current value of this as the new default for this predicate.', self._predicate_panel.SaveCustomDefault )
            
            if self._predicate_panel.UsesCustomDefault():
                
                ClientGUIMenus.AppendSeparator( menu )
                
                ClientGUIMenus.AppendMenuItem( menu, 'reset to original default', 'Clear the custom default value for this predicate.', self._predicate_panel.ClearCustomDefault )
                
            
            CGC.core().PopupMenu( self, menu )
            
        
        def _DoOK( self ):
            
            try:
                
                self._predicate_panel.CheckValid()
                
            except Exception as e:
                
                ClientGUIDialogsMessage.ShowWarning( self, f'Sorry, predicate was not valid: {e}' )
                
                return
                
            
            predicates = self._predicate_panel.GetPredicates()
            
            self._parent.SubPanelOK( predicates )
            
        
        def GetPredicatePanel( self ):
            
            return self._predicate_panel
            
        
        def keyPressEvent( self, event ):
            
            ( modifier, key ) = ClientGUIShortcuts.ConvertKeyEventToSimpleTuple( event )
            
            if key in ( QC.Qt.Key_Enter, QC.Qt.Key_Return ):
                
                self._DoOK()
                
            else:
                
                event.ignore()
                
            
        
    

class TagContextButton( ClientGUICommon.BetterButton ):
    
    valueChanged = QC.Signal( ClientSearch.TagContext )
    
    def __init__( self, parent: QW.QWidget, tag_context: ClientSearch.TagContext, use_short_label = False ):
        
        self._tag_context = ClientSearch.TagContext()
        
        self._use_short_label = use_short_label
        
        ClientGUICommon.BetterButton.__init__( self, parent, 'initialising', self._Edit )
        
        self.SetValue( tag_context )
        
    
    def _Edit( self ):
        
        services_manager = CG.client_controller.services_manager
        
        service_types_in_order = [ HC.LOCAL_TAG, HC.TAG_REPOSITORY, HC.COMBINED_TAG ]
        
        services = services_manager.GetServices( service_types_in_order )
        
        menu = ClientGUIMenus.GenerateMenu( self )
        
        last_seen_service_type = None
        
        for service in services:
            
            if last_seen_service_type is not None and last_seen_service_type != service.GetServiceType():
                
                ClientGUIMenus.AppendSeparator( menu )
                
            
            tag_context = ClientSearch.TagContext( service_key = service.GetServiceKey() )
            
            ClientGUIMenus.AppendMenuCheckItem( menu, service.GetName(), 'Change the current tag domain to {}.'.format( service.GetName() ), tag_context == self._tag_context, self.SetValue, tag_context )
            
            last_seen_service_type = service.GetServiceType()
            
        
        CGC.core().PopupMenu( self, menu )
        
    
    def GetValue( self ) -> ClientSearch.TagContext:
        
        return self._tag_context
        
    
    def SetValue( self, tag_context: ClientSearch.TagContext ):
        
        original_tag_context = self._tag_context
        
        tag_context = tag_context.Duplicate()
        
        tag_context.FixMissingServices( CG.client_controller.services_manager.FilterValidServiceKeys )
        
        self._tag_context = tag_context
        
        label = self._tag_context.ToString( CG.client_controller.services_manager.GetName )
        
        if self._use_short_label:
            
            self.setText( 'tags' )
            
        else:
            
            self.setText( label )
            
        
        self.setToolTip( ClientGUIFunctions.WrapToolTip( label ) )
        
        if self._tag_context != original_tag_context:
            
            self.valueChanged.emit( self._tag_context )
            
        
    
