<form action="GLS_WS_GetExpCli_Request_Example.php" method="get">
<br><b>INTRODUCE THIS INFORMATION::</b><br><br>
UId Client.: <input type="text" name="UIdCli"     size="40" value=""> ............... (Example: 7B530D2A-B9C7-46C8-BB6C-xxxxxxxxxxxx)<br><br>
Reference..: <input type="text" name="Referencia" size="40" value=""> ............... (The customer reference of shipment)<br>
<br><br>
<input type="submit" value="Submit">
</form>

<?php
//**********************************************************
// AUTOR..........: ALBERT ROIG.
// CREATION DATA..: 25/01/2017.
// NOTES..........: Example of obtaining feedback of shipment
//**********************************************************


        //=================================================================================================================
        // DATOS NECESARIOS PARA BUSCAR ENVIOS   (UID DE CLIENTE Y REFERENCIA ENVÍO).
		// DATA REQUIRED TO SEARCH FOR SHIPMENTS (CUSTOMER UID AND SHIPMENT REFERENCE).
        //=================================================================================================================
        $uidCliente = $_GET['UIdCli'];
        $Busca      = $_GET['Referencia'];

        if ($uidCliente == "") $uidCliente = "7B530D2A-B9C7-46C8-BB6C-xxxxxxxxxxxx";
        if ($Busca      == "") $Busca      = "1234561002";
        
        //=================================================================================================================
        // PREPARAR LLAMADA A MÉTODO WEBSERVICE.
		// PREPARE CALL TO WEBSERVICE METHOD.
        //=================================================================================================================

        $URL= "https://wsclientes.asmred.com/b2b.asmx?wsdl";

        $XML= '<?xml version="1.0" encoding="utf-8"?>
               <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
                 <soap12:Body>
                   <GetExpCli xmlns="http://www.asmred.com/">
                     <codigo>' . $Busca . '</codigo>
                     <uid>' . $uidCliente . '</uid>
                   </GetExpCli>
                 </soap12:Body>
               </soap12:Envelope>';

        $ch = curl_init();
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, TRUE);
        curl_setopt($ch, CURLOPT_SSL_VERIFYPEER, FALSE);
        curl_setopt($ch, CURLOPT_HEADER, FALSE);
        curl_setopt($ch, CURLOPT_FORBID_REUSE, TRUE);
        curl_setopt($ch, CURLOPT_FRESH_CONNECT, TRUE);
        curl_setopt($ch, CURLOPT_URL, $URL );
        curl_setopt($ch, CURLOPT_POSTFIELDS, $XML );
        curl_setopt($ch, CURLOPT_HTTPHEADER, Array("Content-Type: text/xml; charset=UTF-8"));

        $postResult = curl_exec($ch);
        curl_close($ch);


        //echo 'uidCliente: ' . $uidCliente . '<br><br>';;
        //echo 'xml: ' . $XML . '<br><br>';
        //echo 'postResult: ' . $postResult . '<br><br>';

        $xml = simplexml_load_string($postResult, NULL, NULL, "http://http://www.w3.org/2003/05/soap-envelope");
        $xml->registerXPathNamespace('asm', 'http://www.asmred.com/');
        $arr = $xml->xpath("//asm:GetExpCliResponse/asm:GetExpCliResult");

        if (sizeof($arr) == 0)
           echo '<font size="5">Posiblemente el "UID Cliente" está mal informado.</font>';
        else {
           $ret2 = $arr[0]->xpath("//expediciones/exp");
           
           if ($ret2 == null)
              echo '<font size="5">Ningún envío encontrado con la referencia: ' . $Busca . '</font>';
              echo '<font size="5">No shipment found with reference: ' . $Busca . '</font>';
           else {
           
              echo '<font size="7">' . sizeof($ret2) . '</font> envíos encontrados con la referencia: ' . $Busca . '<br><br><br>';
              echo '<font size="7">' . sizeof($ret2) . '</font> shipments found with reference: ' . $Busca . '<br><br><br>';
              
              $Num = 0;
              foreach ($ret2 as $ret) {
                 
                 $Num2 = $Num + 1;
              
                 //=================================================================================================================
                 // RECOGER DATOS DE EXPEDICION.
				 // GET SHIPMENT DATA.
                 //=================================================================================================================
                 $expedicion       = $ret[0]->xpath("//expediciones/exp/expedicion");
                 $albaran          = $ret[0]->xpath("//expediciones/exp/albaran");
                 $codexp           = $ret[0]->xpath("//expediciones/exp/codexp");
                 $codbar           = $ret[0]->xpath("//expediciones/exp/codbar");
                 $uidExp           = $ret[0]->xpath("//expediciones/exp/uidExp");
                                                                                        
                 $codplaza_cli     = $ret[0]->xpath("//expediciones/exp/codplaza_cli");
                 $codcli           = $ret[0]->xpath("//expediciones/exp/codcli");
                 $nmCliente        = $ret[0]->xpath("//expediciones/exp/nmCliente");
                                                                                        
                 $fecha            = $ret[0]->xpath("//expediciones/exp/fecha");
                 $FPEntrega        = $ret[0]->xpath("//expediciones/exp/FPEntrega");
                                                                                        
                 $nombre_org       = $ret[0]->xpath("//expediciones/exp/nombre_org");
                 $nif_org          = $ret[0]->xpath("//expediciones/exp/nif_org");
                 $calle_org        = $ret[0]->xpath("//expediciones/exp/calle_org");
                 $localidad_org    = $ret[0]->xpath("//expediciones/exp/localidad_org");
                 $cp_org           = $ret[0]->xpath("//expediciones/exp/cp_org");
                 $tfno_org         = $ret[0]->xpath("//expediciones/exp/tfno_org");
                 $departamento_org = $ret[0]->xpath("//expediciones/exp/departamento_org");
                 $codpais_org      = $ret[0]->xpath("//expediciones/exp/codpais_org");
                                                                                        
                 $nombre_dst       = $ret[0]->xpath("//expediciones/exp/nombre_dst");
                 $nif_dst          = $ret[0]->xpath("//expediciones/exp/nif_dst");
                 $calle_dst        = $ret[0]->xpath("//expediciones/exp/calle_dst");
                 $localidad_dst    = $ret[0]->xpath("//expediciones/exp/localidad_dst");
                 $cp_dst           = $ret[0]->xpath("//expediciones/exp/cp_dst");
                 $tfno_dst         = $ret[0]->xpath("//expediciones/exp/tfno_dst");
                 $departamento_dst = $ret[0]->xpath("//expediciones/exp/departamento_dst");
                 $codpais_dst      = $ret[0]->xpath("//expediciones/exp/codpais_dst");
                                                                                        
                 $codServicio      = $ret[0]->xpath("//expediciones/exp/codServicio");
                 $codHorario       = $ret[0]->xpath("//expediciones/exp/codHorario");
                 $servicio         = $ret[0]->xpath("//expediciones/exp/servicio");
                 $horario          = $ret[0]->xpath("//expediciones/exp/horario");
                                                                                        
                 $tipo_portes      = $ret[0]->xpath("//expediciones/exp/tipo_portes");
                 $bultos           = $ret[0]->xpath("//expediciones/exp/bultos");
                 $kgs              = $ret[0]->xpath("//expediciones/exp/kgs");
                 $vol              = $ret[0]->xpath("//expediciones/exp/vol");
                 $Observacion      = $ret[0]->xpath("//expediciones/exp/Observacion");
                 $dac              = $ret[0]->xpath("//expediciones/exp/dac");
                 $retorno          = $ret[0]->xpath("//expediciones/exp/retorno");
                                                                                        
                 $borrado          = $ret[0]->xpath("//expediciones/exp/borrado");
                 $codestado        = $ret[0]->xpath("//expediciones/exp/codestado");
                 $estado           = $ret[0]->xpath("//expediciones/exp/estado");
                 $incidencia       = $ret[0]->xpath("//expediciones/exp/incidencia");
              
                 //=================================================================================================================
                 // MOSTRAR DATOS DE EXPEDICION.
				 // SHOW EXPEDITION DATA.
                 //=================================================================================================================
                 echo '<strong><font size="5">ENVIO NÚMERO (SHIPMENT NUMBER) ' . $Num2 . '</font></strong><br><br>';
                 
                 echo'<BLOCKQUOTE>';
                 echo '<strong>Datos de identificación (Identification information)</strong><br>';
                 echo '<table border="1" bgcolor="0#b0">';
                 echo '<tr>';
                 echo '<td><strong>Envío</strong></td>';
                 echo '<td><strong>Expedición</strong></td>';
                 echo '<td><strong>Albarán</strong></td>';
                 echo '<td><strong>Cod.Exp</strong></td>';
                 echo '<td><strong>Cod.Barras</strong></td>';
                 echo '<td><strong>Uid.Exp</strong></td>';
                 echo '</tr>';
                 echo '<tr>';
                 echo '<td>' . '#' . $Num2 . '</td>';
                 echo '<td>' . $expedicion[$Num] . '</td>';
                 echo '<td>' . $albaran[$Num] . '</td>';
                 echo '<td>' . $codexp[$Num] . '</td>';
                 echo '<td>' . $codbar[$Num] . '</td>';
                 echo '<td>' . $uidExp[$Num] . '</td>';
                 echo '</tr></table><br>';
              
                 echo '<strong>Datos de envío (Shipment information)</strong><br>';
                 echo '<table border="1" bgcolor="0#b0">';
                 echo '<tr>';
                 echo '<td><strong>Plaza Paga</strong></td>';
                 echo '<td><strong>Cod.Cliente</strong></td>';
                 echo '<td><strong>Nom.Cliente</strong></td>';
                 echo '<td><strong>Fec.Envío</strong></td>';
                 echo '<td><strong>Fec.Prev.Entrega</strong></td>';
                 echo '</tr>';
                 echo '<tr>';
                 echo '<td>' . $codplaza_cli[$Num] . '</td>';
                 echo '<td>' . $codcli[$Num] . '</td>';
                 echo '<td>' . $nmCliente[$Num] . '</td>';
                 echo '<td>' . $fecha[$Num] . '</td>';
                 echo '<td>' . $FPEntrega[$Num] . '</td>';
                 echo '</tr></table><br>';
              
                 echo '<strong>Datos de Remitente (Sender information)</strong><br>';
                 echo '<table border="1" bgcolor="#f#f0">';
                 echo '<tr>';
                 echo '<td><strong>Nombre</strong></td>';
                 echo '<td><strong>Nif</strong></td>';
                 echo '<td><strong>Dirección</strong></td>';
                 echo '<td><strong>Localidad</strong></td>';
                 echo '<td><strong>Cod.Postal</strong></td>';
                 echo '<td><strong>Teléfono</strong></td>';
                 echo '<td><strong>Departamento</strong></td>';
                 echo '<td><strong>CodPais</strong></td>';
                 echo '</tr>';
                 echo '<tr>';
                 echo '<td>' . $nombre_org[$Num] . '</td>';
                 echo '<td>' . $nif_org[$Num] . '</td>';
                 echo '<td>' . $calle_org[$Num] . '</td>';
                 echo '<td>' . $localidad_org[$Num] . '</td>';
                 echo '<td>' . $cp_org[$Num] . '</td>';
                 echo '<td>' . $tfno_org[$Num] . '</td>';
                 echo '<td>' . $departamento_org[$Num] . '</td>';
                 echo '<td>' . $codpais_org[$Num] . '</td>';
                 echo '</tr></table><br>';
              
                 echo '<strong>Datos de Destinatario (Consignee information)</strong><br>';
                 echo '<table border="1" bgcolor="#f#f0">';
                 echo '<tr>';
                 echo '<td><strong>Nombre</strong></td>';
                 echo '<td><strong>Nif</strong></td>';
                 echo '<td><strong>Dirección</strong></td>';
                 echo '<td><strong>Localidad</strong></td>';
                 echo '<td><strong>Cod.Postal</strong></td>';
                 echo '<td><strong>Teléfono</strong></td>';
                 echo '<td><strong>Departamento</strong></td>';
                 echo '<td><strong>CodPais</strong></td>';
                 echo '</tr>';
                 echo '<tr>';
                 echo '<td>' . $nombre_dst[$Num] . '</td>';
                 echo '<td>' . $nif_dst[$Num] . '</td>';
                 echo '<td>' . $calle_dst[$Num] . '</td>';
                 echo '<td>' . $localidad_dst[$Num] . '</td>';
                 echo '<td>' . $cp_dst[$Num] . '</td>';
                 echo '<td>' . $tfno_dst[$Num] . '</td>';
                 echo '<td>' . $departamento_dst[$Num] . '</td>';
                 echo '<td>' . $codpais_dst[$Num] . '</td>';
                 echo '</tr></table><br>';
              
                 echo '<strong>Otros datos (another information)</strong><br>';
                 echo '<table border="1" bgcolor="#c#c#c">';
                 echo '<tr>';
                 echo '<td><strong>Cod.Servicio</strong></td>';
                 echo '<td><strong>Nom.Servicio</strong></td>';
                 echo '<td><strong>Cod.Horario</strong></td>';
                 echo '<td><strong>Nom.Horario</strong></td>';
                 echo '<td><strong>Portes</strong></td>';
                 echo '<td><strong>Bultos</strong></td>';
                 echo '<td><strong>Kgs</strong></td>';
                 echo '<td><strong>Volumen</strong></td>';
                 echo '<td><strong>Observaciones</strong></td>';
                 echo '<td><strong>RCS</strong></td>';
                 echo '<td><strong>Retorno</strong></td>';
                 echo '<td><strong>Borrado</strong></td>';
                 echo '<td><strong>Cod.Estado.Actual</strong></td>';
                 echo '<td><strong>Nom.Estado.Actual</strong></td>';
                 echo '<td><strong>Nom.Incidencia.Actual</strong></td>';
                 echo '</tr>';
                 echo '<tr>';
                 echo '<td>' . $codServicio[$Num] . '</td>';
                 echo '<td>' . $servicio[$Num] . '</td>';
                 echo '<td>' . $codHorario[$Num] . '</td>';
                 echo '<td>' . $horario[$Num] . '</td>';
                 echo '<td>' . $tipo_portes[$Num] . '</td>';
                 echo '<td>' . $bultos[$Num] . '</td>';
                 echo '<td>' . $kgs[$Num] . '</td>';
                 echo '<td>' . $vol[$Num] . '</td>';
                 echo '<td>' . $Observacion[$Num] . '</td>';
                 echo '<td>' . $dac[$Num] . '</td>';
                 echo '<td>' . $retorno[$Num] . '</td>';
                 echo '<td>' . $borrado[$Num] . '</td>';
                 echo '<td>' . $codestado[$Num] . '</td>';
                 echo '<td>' . $estado[$Num] . '</td>';
                 echo '<td>' . $incidencia[$Num] . '</td>';
                 echo '</tr></table><br>';
              
                 //=================================================================================================================
                 // MOSTRAR TRACKING.
				 // SHOW TRACKING.
                 //=================================================================================================================
                 echo '<strong>Historial (Tracking)</strong><br>';
                 echo '<table border="1" bgcolor="0#f0">';
                 echo '<tr>';
                 echo '<td><strong>Fecha</strong></td>';
                 echo '<td><strong>Tipo</strong></td>';
                 echo '<td><strong>Código</strong></td>';
                 echo '<td><strong>Descripción</strong></td>';
                 echo '<td><strong>Cod.Agencia</strong></td>';
                 echo '<td><strong>Nom.Agencia</strong></td>';
                 echo '</tr>';
              
                 $ret3 = $ret2[$Num]->xpath("tracking_list/tracking");
                 $Num3 = 0;
                 foreach ($ret3 as $ret) {
                    $TrkFecha   = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/fecha");
                    $TrkTipo    = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/tipo");
                    $TrkCodigo  = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/codigo");
                    $TrkDesc    = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/evento");
                    $TrkCodAge  = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/plaza");
                    $TrkNomAge  = $ret[0]->xpath("//expediciones/exp/tracking_list/tracking/nombreplaza");
                    
                    echo '<tr>';
                    echo '<td>' . $TrkFecha[$Num3]  . '</td>';
                    echo '<td>' . $TrkTipo[$Num3]   . '</td>';
                    echo '<td>' . $TrkCodigo[$Num3] . '</td>';
                    echo '<td>' . $TrkDesc[$Num3]   . '</td>';
                    echo '<td>' . $TrkCodAge[$Num3] . '</td>';
                    echo '<td>' . $TrkNomAge[$Num3] . '</td>';
                    echo '</tr>';
                    
                    $Num3 = $Num3 + 1;
                 }
                 echo '</table><br>';
                 
                 //=================================================================================================================
                 // MOSTRAR DIGITALIZACIONES.
				 // SHOW DIGITIZATIONS.
                 //=================================================================================================================
                 echo '<strong>Digitalizaciones (images)</strong><br>';
                 echo '<table border="1" bgcolor="#a#f#f">';
                 echo '<tr>';
                 echo '<td><strong>Fecha</strong></td>';
                 echo '<td><strong>Código</strong></td>';
                 echo '<td><strong>Tipo</strong></td>';
                 echo '<td><strong>Imagen</strong></td>';
                 echo '<td><strong>Observaciones</strong></td>';
                 echo '</tr>';
                 
                 $ret4 = $ret2[$Num]->xpath("digitalizaciones/digitalizacion");
                 $Num4 = 0;
              
                 foreach ($ret4 as $ret) {
                    $DigFecha   = $ret[0]->xpath("//expediciones/exp/digitalizaciones/digitalizacion/fecha");
                    $DigCodigo  = $ret[0]->xpath("//expediciones/exp/digitalizaciones/digitalizacion/codtipo");
                    $DigTipo    = $ret[0]->xpath("//expediciones/exp/digitalizaciones/digitalizacion/tipo");
                    $DigImag    = $ret[0]->xpath("//expediciones/exp/digitalizaciones/digitalizacion/imagen");
                    $DigObserv  = $ret[0]->xpath("//expediciones/exp/digitalizaciones/digitalizacion/observaciones");
              
                    echo '<tr>';
                    echo '<td>' . $DigFecha[$Num4]  . '</td>';
                    echo '<td>' . $DigCodigo[$Num4] . '</td>';
                    echo '<td>' . $DigTipo[$Num4]   . '</td>';
                    echo '<td>' . '<a href="' . $DigImag[$Num4] . '">Ver pod</a>'  . '</td>';
                    echo '<td>' . $DigObserv[$Num4] . '</td>';
                    echo '</tr>';
              
                    $Num4 = $Num4 + 1;
                 }
                 echo '</table><br>';
                 echo'</BLOCKQUOTE>';
              
                 $Num = $Num + 1;
              }
              echo '</table>';
           }
        }
?>