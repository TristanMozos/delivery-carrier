<?php

   //**********************************************************
   // AUTHOR..........: ALBERT ROIG.
   // CREATION DATA...: 06/03/2017.
   // NOTES...........: Example of shipment insertion.
   //**********************************************************

   $uidCliente="6BAB7A53-3B6D-4D5A-9450-702D2FAC0B11";

   $URL= "https://wsclientes.asmred.com/b2b.asmx?wsdl";

   $envio = array();
   $envio["fecha"] = "02/04/2017";
   $envio["servicio"] = "1";
   $envio["horario"] = "3";
   $envio["bultos"] = "1";
   $envio["peso"] = "1";
   $envio["reem"] = "0";
   $envio["nombreOrg"] = "from name";
   $envio["direccionOrg"] = "from address";
   $envio["poblacionOrg"] = "from city";
   $envio["codPaisOrg"] = "ES";
   $envio["cpOrg"] = "08100";
   $envio["nombreDst"] = "consignee name";
   $envio["direccionDst"] = "consignee address";
   $envio["poblacionDst"] = "consignee city";
   $envio["codPaisDst"] = "ES";
   $envio["cpDst"] = "28004";
   $envio["tfnoDst"] = "935936688";
   $envio["emailDst"] = "test@test.com";
   $envio["observaciones"] = "transport notes";
   $envio["nif"] = "11223344F";
   $envio["portes"] = "P";
   $envio["RefC"] = "1234561002";

   $XML= '<?xml version="1.0" encoding="utf-8"?>
         <soap12:Envelope xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:xsd="http://www.w3.org/2001/XMLSchema" xmlns:soap12="http://www.w3.org/2003/05/soap-envelope">
         <soap12:Body>
         <GrabaServicios  xmlns="http://www.asmred.com/">
         <docIn>
            <Servicios uidcliente="' . $uidCliente . '" xmlns="http://www.asmred.com/">
            <Envio>
               <Fecha>' . $envio["fecha"] . '</Fecha>
               <Servicio>' . $envio["servicio"] . '</Servicio>
               <Horario>' . $envio["horario"] . '</Horario>
               <Bultos>' . $envio["bultos"] . '</Bultos>
               <Peso>' . $envio["peso"] . '</Peso>
               <Portes>' . $envio["portes"] . '</Portes>
               <Importes>
                  <Reembolso>'. $envio["reem"] .'</Reembolso>
               </Importes>
               <Remite>
                  <Nombre>' . $envio["nombreOrg"] . '</Nombre>
                  <Direccion>' . $envio["direccionOrg"] . '</Direccion>
                  <Poblacion>' . $envio["poblacionOrg"] . '</Poblacion>
                  <Pais>' . $envio["codPaisOrg"] . '</Pais>
                  <CP>' . $envio["cpOrg"] . '</CP>
               </Remite>
               <Destinatario>
                  <Nombre>' . $envio["nombreDst"] . '</Nombre>
                  <Direccion>' . $envio["direccionDst"] . '</Direccion>
                  <Poblacion>' . $envio["poblacionDst"] . '</Poblacion>
                  <Pais>' . $envio["codPaisDst"]. '</Pais>
                  <CP>' . $envio["cpDst"] . '</CP>
                  <Telefono>' . $envio["tfnoDst"] . '</Telefono>
                  <Email>' . $envio["emailDst"] . '</Email>
                  <NIF>' . $envio["nif"] . '</NIF>
                  <Observaciones>' . $envio["observaciones"] . '</Observaciones>
               </Destinatario>
               <Referencias>
                  <Referencia tipo="C">' . $envio["RefC"] . '</Referencia>
               </Referencias>
            </Envio>
            </Servicios>
            </docIn>
         </GrabaServicios>
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

   //echo 'xml: ' . $XML . '<br><br>';

   $postResult = curl_exec($ch);
   curl_close($ch);
   //echo 'postResult: ' . $postResult . '<br><br>';


   $xml = simplexml_load_string($postResult, NULL, NULL, "http://http://www.w3.org/2003/05/soap-envelope");
   $xml->registerXPathNamespace('asm', 'http://www.asmred.com/');
   $arr = $xml->xpath("//asm:GrabaServiciosResponse/asm:GrabaServiciosResult");
   $ret = $arr[0]->xpath("//Servicios/Envio");

   $return = $ret[0]->xpath("//Servicios/Envio/Resultado/@return");
   echo 'Return: ' . $return[0] . '<br/><br/>';

   $cb = $ret[0]->xpath("//Servicios/Envio/@codbarras");
   echo 'Codigo barras: ' . $cb[0]["codbarras"];

   $uid = $ret[0]->xpath("//Servicios/Envio/@uid");
   echo '<br/>uid: ' . $uid[0]["uid"];

?>